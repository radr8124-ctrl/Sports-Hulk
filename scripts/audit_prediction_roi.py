#!/usr/bin/env python3
"""ROI accounting: fills include spread/slippage; unknown costs block profit claims."""
import json,math
from decimal import Decimal
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def number(value):
 if isinstance(value,bool):raise ValueError('Boolean amount')
 x=Decimal(str(value))
 if not x.is_finite():raise ValueError('Nonfinite amount')
 return x
def summarize(trades,mode):
 if mode not in ('PAPER','ACTUAL'):raise ValueError('Unknown accounting mode')
 ids=set();settled=[];pending=0
 for r in trades:
  if r.get('mode')!=mode:raise ValueError('Cannot combine simulated and actual returns')
  identity=r.get('trade_id')
  if not identity or identity in ids:raise ValueError('Duplicate or missing trade identity')
  ids.add(identity)
  if r.get('settled') is not True:pending+=1;continue
  if r.get('fees_verified') is not True or r.get('settlement_verified') is not True:
   return dict(status='COST_OR_SETTLEMENT_UNVERIFIED',mode=mode,net_profit=None,net_roi=None,maximum_drawdown=None,settled_trades=0,pending_trades=pending,submitted_records=len(trades))
  q=number(r['quantity']);price=number(r['fill_price']);fee=number(r['entry_fee']);exit_fee=number(r['exit_fee']);payout=number(r['settlement_per_contract'])
  if q<=0 or not 0<price<1 or fee<0 or exit_fee<0 or not 0<=payout<=1:raise ValueError('Invalid contract accounting amounts')
  at=datetime.fromisoformat(r['settled_at_utc'].replace('Z','+00:00'))
  if at.tzinfo is None:raise ValueError('Settlement clock needs timezone')
  cost=q*price+fee;profit=q*payout-cost-exit_fee
  settled.append((at,identity,cost,profit))
 if not settled:return dict(status='NO_SETTLED_TRADES',mode=mode,net_profit=None,net_roi=None,maximum_drawdown=None,settled_trades=0,pending_trades=pending,submitted_records=len(trades))
 total=sum((x[2] for x in settled),Decimal(0));net=sum((x[3] for x in settled),Decimal(0))
 equity=peak=drawdown=Decimal(0)
 for at,identity,cost,profit in sorted(settled):
  equity+=profit;peak=max(peak,equity);drawdown=max(drawdown,peak-equity)
 return dict(status='SETTLED_PAPER_ACCOUNTING' if mode=='PAPER' else 'SETTLED_ACTUAL_ACCOUNTING',mode=mode,net_profit=float(net),net_roi=float(net/total),settled_capital_including_entry_fees=float(total),maximum_drawdown=float(drawdown),settled_trades=len(settled),pending_trades=pending,submitted_records=len(trades))
def main():
 from prediction_clv import summarize_clv
 source=ROOT/'nfl_live/prediction_markets/nfl_roi_paper_trades.jsonl'
 trades=[json.loads(s) for s in source.read_text().splitlines() if s.strip()] if source.exists() else []
 report=summarize(trades,'PAPER')
 report['closing_line_value']=summarize_clv(trades,'PAPER')
 observation=json.loads((ROOT/'nfl_live/prediction_markets/nfl_narrow_forward_quotes_latest.json').read_text())
 report.update(schema='zenith.prediction.roi_status.v1',checked_at_utc=datetime.now(timezone.utc).isoformat(),primary_objective='NET_ROI_AFTER_ALL_COSTS',scope='NFL game winners; existing frozen model',observed_games=observation['observed_games'],observed_outcomes=observation['observed_outcomes'],observations_captured_at_utc=observation['captured_at_utc'],trade_ledger_present=source.exists(),validated_profitable_edge=False,actual_trades=0,approved_picks=0,remaining=['Freeze a selection and sizing rule before outcomes','Verify contract-specific fees and settlement treatment','Record forward paper entries and actual execution assumptions','Grade every selection including losses; assess ROI uncertainty'])
 output=ROOT/'nfl_live/prediction_markets/prediction_roi_status_latest.json';output.write_text(json.dumps(report,indent=2)+'\n')
 public=ROOT/'commercial_web/public/prediction_market_nfl_evidence.json';data=json.loads(public.read_text());data['roi_validation']=report;public.write_text(json.dumps(data,indent=2)+'\n')
 print(json.dumps(report))
if __name__=='__main__':main()
