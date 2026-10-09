"""Read-only historical player-prop evidence pilot.

Hugging Face provider rows are matched against official MLB boxscore history.
This does NOT produce forward predictions, modify model gates, or submit picks.
Source: https://huggingface.co/datasets/SmartStake/mlb-player-props
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import unicodedata

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_HISTORY = ROOT / 'intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_HISTORY.csv'
SOURCE_REPO = 'SmartStake/mlb-player-props'
SOURCE_LICENSE = 'cc-by-4.0 (dataset card; verify upstream bookmaker data rights before deployment)'

HITTING_MARKETS = {
    'player bases': 'total_bases',
    'player hits': 'hits',
    'player rbis': 'rbi',
    'player home runs': 'home_runs',
    'player batting walks': 'walks',
}
MARKETS = {**HITTING_MARKETS, 'player strikeouts': 'strikeouts'}
REQUIRED_OFFICIAL_COLUMNS = ['game_pk', 'official_date', 'game_date', 'game_type', 'status',
                             'player', 'group', 'team', 'opponent', *set(MARKETS.values())]


def clean_player_name(name: object) -> str:
    """Case/diacritic normalization, but no fuzzy merges of distinct players."""
    ascii_name = unicodedata.normalize('NFKD', str(name or '')).encode('ascii', 'ignore').decode('ascii').lower()
    return re.sub('[^a-z0-9]', '', ascii_name)


def safe_number(value: object) -> float | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def market_implied_probability(decimal_odds: object) -> float | None:
    odds = safe_number(decimal_odds)
    if odds is None or odds <= 1 or odds > 1000:
        return None
    return 1.0 / odds


def fair_grade_from_stat(side: object, line: object, actual: object) -> bool | None:
    side = str(side or '').strip().lower()
    actual_value, line_value = safe_number(actual), safe_number(line)
    if actual_value is None or line_value is None or side not in {'over', 'under'}:
        return None
    if actual_value == line_value:
        return None  # Push is not an independently graded WIN/LOSS.
    return actual_value > line_value if side == 'over' else actual_value < line_value


def _utc_timestamp(value: object) -> pd.Timestamp | None:
    if value is None or not str(value).strip():
        return None
    try:
        # The external sample contains naive times. Treating those as UTC is
        # only acceptable when independently confirmed by an official kickoff.
        stamp = pd.Timestamp(value)
        return stamp.tz_localize('UTC') if stamp.tz is None else stamp.tz_convert('UTC')
    except (TypeError, ValueError, OverflowError):
        return None


def _official_frame(history: pd.DataFrame) -> pd.DataFrame:
    required = {'game_pk', 'game_date', 'player', 'group', 'game_type', 'status'}
    if not required.issubset(history.columns):
        raise ValueError(f'Official history missing: {sorted(required - set(history.columns))}')
    frame = history.copy()
    frame = frame[frame['game_type'].astype(str).str.upper().eq('R')].copy()
    frame = frame[frame['status'].astype(str).str.upper().isin(['FINAL', 'COMPLETED EARLY'])].copy()
    frame['_player_key'] = frame['player'].map(clean_player_name)
    frame['_official_start'] = pd.to_datetime(frame['game_date'], errors='coerce', utc=True)
    frame = frame[frame['_official_start'].notna() & frame['_player_key'].ne('')].copy()
    return frame


def audit_rows(provider_rows: list[dict], official_history: pd.DataFrame, *, max_start_delta_minutes: float = 3.0) -> list[dict]:
    """Fail closed whenever identity, timing, outcome, or settlement disagrees.

    Only the provider's odds/line/side and a verified participant/game identity
    enter historical prediction evaluation; the official post-game stat is
    used exclusively for outcome verification.
    """
    official = _official_frame(official_history)
    by_player = {key: group for key, group in official.groupby('_player_key')}
    audited = []
    for source_row in provider_rows:
        item = dict(source_row)
        base = {key: item.get(key) for key in (
            'sample_index', 'offset', 'game_id', 'start_time', 'ts', 'player',
            'market', 'side', 'line', 'book', 'odds', 'result', 'won')}
        base['provider_game_id'] = base['game_id']
        base['source_repo'] = SOURCE_REPO
        base['source_license'] = SOURCE_LICENSE
        base['timestamp_timezone_assumed'] = 'UTC (official kickoff verification required)'
        base['status'] = 'UNVERIFIED'

        def reject(reason: str) -> None:
            base['status'] = reason
            audited.append(base)

        market = str(item.get('market') or '').strip().lower()
        if market not in MARKETS:
            reject('UNSUPPORTED_MARKET')
            continue
        if market_implied_probability(item.get('odds')) is None or safe_number(item.get('line')) is None or not str(item.get('book') or '').strip():
            reject('INVALID_ODDS_OR_LINE')
            continue
        if str(item.get('side') or '').lower() not in {'over', 'under'}:
            reject('INVALID_SIDE')
            continue
        ts = _utc_timestamp(item.get('ts'))
        source_start = _utc_timestamp(item.get('start_time'))
        if ts is None or source_start is None:
            reject('INVALID_TIMESTAMP')
            continue
        if ts >= source_start:
            reject('NOT_PREGAME_AT_PROVIDER_START')
            continue
        candidate = by_player.get(clean_player_name(item.get('player')))
        if candidate is None:
            reject('NO_UNIQUE_PLAYER_GAME_MATCH')
            continue
        candidates = candidate.copy()
        if market in HITTING_MARKETS:
            candidates = candidates[candidates['group'].astype(str).str.upper().eq('HITTING')]
        candidates['_delta_min'] = (candidates['_official_start'] - source_start).abs().dt.total_seconds() / 60
        candidates = candidates[candidates['_delta_min'] <= max_start_delta_minutes]
        if len(candidates) != 1:
            base['candidate_count'] = len(candidates)
            reject('NO_UNIQUE_PLAYER_GAME_MATCH')
            continue
        match = candidates.iloc[0]
        base.update({
            'official_game_pk': int(match['game_pk']),
            'official_start': match['_official_start'].isoformat(),
            'kickoff_difference_minutes': round(float(match['_delta_min']), 3),
            'official_player': match['player'],
            'official_team': match.get('team'),
            'official_opponent': match.get('opponent'),
            'official_group': match['group'],
        })
        base['timestamp_before_official_start'] = bool(ts < match['_official_start'])
        if not base['timestamp_before_official_start']:
            reject('NOT_PREGAME_AT_OFFICIAL_START')
            continue
        if item.get('won') is None or safe_number(item.get('result')) is None:
            reject('MISSING_VENDOR_OUTCOME')
            continue
        if not isinstance(item.get('won'), bool):
            reject('INVALID_VENDOR_GRADE')
            continue
        stat_column = MARKETS[market]
        if stat_column not in candidates.columns or safe_number(match.get(stat_column)) is None:
            reject('MISSING_OFFICIAL_STAT')
            continue
        official_value = float(match[stat_column])
        base['official_stat'] = official_value
        base['official_stat_name'] = stat_column
        if abs(official_value - float(item['result'])) > 1e-6:
            reject('RESULT_DISAGREES_WITH_OFFICIAL')
            continue
        grade = fair_grade_from_stat(item['side'], item['line'], official_value)
        if grade is None:
            reject('PUSH_OR_UNRESOLVED_OUTCOME')
            continue
        if grade is not item['won']:
            reject('WON_FLAG_DISAGREES_WITH_OFFICIAL')
            continue
        base['market_implied_probability'] = market_implied_probability(item['odds'])
        base['verified_win'] = grade
        base['status'] = 'VERIFIED_HISTORICAL'
        audited.append(base)

    # If one provider event maps to multiple official fixtures, reject its
    # evidence entirely rather than count suspicious bookmaker snapshots.
    crosswalk = {}
    for row in audited:
        if row.get('official_game_pk') is not None:
            crosswalk.setdefault(str(row['provider_game_id']), set()).add(int(row['official_game_pk']))
    conflicting = {key for key, games in crosswalk.items() if len(games) > 1}
    for row in audited:
        if str(row.get('provider_game_id')) in conflicting:
            row['status'] = 'CONFLICTING_PROVIDER_GAME_ID'
            row.pop('verified_win', None)
            row.pop('market_implied_probability', None)
    return audited


def _unique_verified(audit: list[dict]) -> list[dict]:
    valid = [r for r in audit if r.get('status') == 'VERIFIED_HISTORICAL']
    valid.sort(key=lambda r: (str(r.get('official_start')), str(r.get('ts')), str(r.get('provider_game_id'))))
    unique = {}
    for row in valid:
        unique.setdefault(int(row['official_game_pk']), row)
    return sorted(unique.values(), key=lambda r: (r['official_start'], int(r['official_game_pk'])))


def summarize_pilot(audit: list[dict]) -> dict:
    unique = _unique_verified(audit)
    return {
        'sample_rows': len(audit),
        'sample_distinct_provider_games': len({str(r.get('provider_game_id')) for r in audit}),
        'status_counts': dict(sorted(Counter(str(r.get('status')) for r in audit).items())),
        'verified_records': sum(r.get('status') == 'VERIFIED_HISTORICAL' for r in audit),
        'verified_independent_games': len(unique),
        'minimum_25_distinct_games_met': len(unique) >= 25,
        'verified_market_counts': dict(sorted(Counter(r['market'] for r in unique).items())),
        'sampled_vendor_book_counts': dict(sorted(Counter(str(r.get('book')) for r in audit).items())),
        'kickoff_difference_max_minutes_verified': max((r['kickoff_difference_minutes'] for r in unique), default=None),
        'timezone_assumption': 'Vendor timestamps assumed UTC and individually checked against official MLB starts',
        'source': SOURCE_REPO,
        'license_notice': SOURCE_LICENSE,
        'evidence_scope': 'EXTERNAL_HISTORICAL_RESEARCH_ONLY_NO_HULK_FORWARD_PREDICTIONS',
    }


def chronological_split(audit: list[dict], *, train_fraction: float = 0.6) -> tuple[list[dict], list[dict]]:
    if not 0 < train_fraction < 1:
        raise ValueError('Train fraction must be between zero and one.')
    unique = _unique_verified(audit)
    if len(unique) < 2:
        return [], []
    boundary = max(1, min(len(unique) - 1, int(len(unique) * train_fraction)))
    # Whole kickoff-time blocks cannot be in both training and holdout.
    while boundary < len(unique) and unique[boundary - 1]['official_start'] == unique[boundary]['official_start']:
        boundary += 1
    if boundary == len(unique):
        return [], []
    return unique[:boundary], unique[boundary:]


def holdout_diagnostics(train: list[dict], holdout: list[dict]) -> dict:
    if not train or not holdout:
        return {'status': 'INSUFFICIENT_FOR_CHRONOLOGICAL_DEMO'}
    prior = sum(bool(r['verified_win']) for r in train) / len(train)
    brier = lambda values: round(sum(float(v) ** 2 for v in values) / len(values), 6)
    return {
        'status': 'HISTORICAL_PROOF_PILOT_NOT_HULK_MODEL_VALIDATION',
        'training_independent_games': len(train),
        'holdout_independent_games': len(holdout),
        'training_last_game_start': train[-1]['official_start'],
        'holdout_first_game_start': holdout[0]['official_start'],
        'train_empirical_win_rate': round(prior, 6),
        'holdout_market_raw_implied_brier': brier([float(r['market_implied_probability']) - int(r['verified_win']) for r in holdout]),
        'holdout_train_prior_brier': brier([prior - int(r['verified_win']) for r in holdout]),
        'interpretation': 'Illustrative outcome-quality comparison only. Market implied odds include vig; sample is selection-biased, not an independent HULK pregame prediction model.',
    }


def load_official_history(path: Path = OFFICIAL_HISTORY) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False, usecols=REQUIRED_OFFICIAL_COLUMNS)


def run_pilot(sample_path: Path, output_dir: Path) -> dict:
    payload = json.loads(sample_path.read_text())
    records = payload.get('records') if isinstance(payload, dict) else payload
    if not isinstance(records, list) or not records:
        raise ValueError('Need a nonempty, bounded source sample list.')
    if len(records) > 250:
        raise ValueError('Only bounded pilot samples <=250 records are allowed.')
    # Strip provisional matches computed during source discovery: do not
    # trust them instead of rechecking independently from official data.
    allowed = {'sample_index', 'offset', 'game_id', 'start_time', 'ts', 'player',
               'market', 'side', 'line', 'book', 'odds', 'result', 'won'}
    raw = [{key: row[key] for key in allowed if key in row} for row in records]
    history = load_official_history()
    audit = audit_rows(raw, history)
    summary = summarize_pilot(audit)
    train, holdout = chronological_split(audit)
    diagnostics = holdout_diagnostics(train, holdout)
    summary['chronological_holdout'] = diagnostics
    summary['generated_at'] = datetime.now(timezone.utc).isoformat()
    summary['official_source_file'] = str(OFFICIAL_HISTORY.relative_to(ROOT))
    summary['publication_gate'] = 'NOT_APPROVED_FOR_LIVE_MODEL_OR_OFFICIAL_PERFORMANCE'
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir/'audit.json').write_text(json.dumps(audit, indent=2, default=str) + '\n')
    (output_dir/'summary.json').write_text(json.dumps(summary, indent=2, default=str) + '\n')
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description='Read-only HF MLB historic prop / official MLB identity validation')
    ap.add_argument('--input-samples', required=True, type=Path, help='Bounded previously-read Hugging Face samples; no automatic bulk downloads')
    ap.add_argument('--output-dir', required=True, type=Path, help='Research-only, never live betting model directories')
    args = ap.parse_args()
    if 'commercial_web' in args.output_dir.parts or 'decision' in args.output_dir.parts:
        raise SystemExit('Refusing to publish pilot samples into live model/UI or official decision folders')
    result = run_pilot(args.input_samples, args.output_dir)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
