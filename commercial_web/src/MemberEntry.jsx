import React from 'react'
import { ArrowRight, BarChart3, LayoutDashboard, ShieldCheck, Sparkles, Target, Users, Radio } from 'lucide-react'
import { AccountModal, useAuth } from './AuthShell'
import ZenithRefAvatar from './ZenithRefAvatar'
import './memberEntry.css'

const destinations = [
  { title: 'Game Day', route: 'Home', Icon: Radio, color: '#FFD36A', text: 'Follow the slate, check scores, and catch the stories that matter.', action: 'Open Game Day' },
  { title: 'Betting research', route: 'Best Bets', Icon: Target, color: '#FF968B', text: 'Compare candidates, inspect the price and evidence, and know when to pass.', action: 'Explore betting' },
  { title: 'Fantasy', route: 'Fantasy', Icon: Users, color: '#7DE4E1', text: 'Bring your roster into focus with player research, lineup tools, and league context.', action: 'Open Fantasy' },
  { title: 'Survivor', route: 'Survivor', Icon: ShieldCheck, color: '#FFD36A', text: 'Manage your entries, track used teams, and weigh this week against future value.', action: 'Open Survivor' },
  { title: 'Prediction markets', route: 'Prediction Markets', Icon: BarChart3, color: '#7DE4E1', text: 'Inspect matched Kalshi and Polymarket contracts, costs, and validation evidence.', action: 'Compare markets' },
  { title: 'Brain Record', route: 'Brain Record', Icon: LayoutDashboard, color: '#FF968B', text: 'See recorded predictions and results. Judge the brain by its evidence.', action: 'Check the record' },
]

export function DashboardHub({ onNavigate, embedded = false }) {
  const { user, loading } = useAuth()
  const Heading = embedded ? 'h2' : 'h1'
  return <section className="member-page" aria-labelledby="dashboard-hub-title">
    <div className="member-heading">
      <div><p className="member-kicker">Your sports command center</p>
        <Heading id="dashboard-hub-title">{user ? 'Welcome back. Make your next call.' : 'Choose your dashboard.'}</Heading>
        <p>One place for the game, your teams, and the evidence behind each decision.</p></div>
      <button className="member-button member-button-dark" onClick={() => onNavigate(user ? 'Ask' : 'Welcome')}>
        {user ? 'Ask The Ref' : loading ? 'Account & sign in' : 'Sign in / create account'} <ArrowRight size={17} />
      </button>
    </div>
    {!user && <p className="member-note">Explore public research now. Sign in to connect your private fantasy leagues, Survivor entries, and preferences.</p>}
    <div className="member-dashboard-grid">
      {destinations.map(({ title, route, Icon, color, text, action }) => <article key={route} className="member-dashboard-card" style={{ '--card-accent': color }}>
        <div className="member-card-icon"><Icon size={25} /></div>
        <h2>{title}</h2><p>{text}</p>
        <button onClick={() => onNavigate(route)}>{action} <ArrowRight size={17} /></button>
      </article>)}
    </div>
    <div className="member-ref-strip"><ZenithRefAvatar size={68} /><div><h2>Need a second look? Ask The Ref.</h2><p>Bring a matchup or player question. Follow the answer back to its sources.</p></div>
      <button className="member-button member-button-dark" onClick={() => onNavigate('Ask')}><Sparkles size={16} /> Ask The Ref</button></div>
  </section>
}

export default function MemberEntry({ onNavigate }) {
  const { user, loading } = useAuth()
  return <div className="member-page">
    <section className="member-entry-grid" aria-labelledby="member-entry-title">
      <div className="member-promo">
        <p className="member-kicker">Sports Zenith · Sports intelligence</p>
        <h1 id="member-entry-title">Know the game.<br /><span>Make the smarter call.</span></h1>
        <p className="member-lead">Your game-day research, fantasy teams, and Survivor strategy. Together, with The Ref in your corner.</p>
        <div className="member-promo-actions"><button className="member-button member-button-coral" onClick={() => onNavigate('Dashboards')}>Explore the dashboards <ArrowRight size={17} /></button>
          <button className="member-text-button" onClick={() => onNavigate('Home')}>See Game Day <ArrowRight size={16} /></button></div>
        <div className="member-product-preview" aria-label="Sports Zenith feature preview">
          <div className="member-preview-top"><span>The Ref's playbook</span><span>Research → decision</span></div>
          <div className="member-preview-body"><ZenithRefAvatar size={115} /><div><h2>Get the call.<br />Check the evidence.</h2><p>Matchups. Players. Price. Risk.</p></div></div>
          <div className="member-preview-bottom"><span>Compare the price</span><span>Know the risk</span><span>Track the result</span></div>
        </div>
      </div>
      <div className="member-signin">
        {loading ? <div className="member-session" role="status">Checking your account…</div> : user ? <div className="member-session"><ShieldCheck size={32} /><h2>You're signed in.</h2><p>Your dashboards are ready. Private features use your verified account.</p><button className="member-button member-button-dark" onClick={() => onNavigate('Dashboards')}>Go to dashboards <ArrowRight size={17} /></button></div>
          : <AccountModal inline onClose={() => onNavigate('Dashboards')} />}
      </div>
    </section>
    <section className="member-value-section" aria-labelledby="member-value-title">
      <p className="member-kicker">The advantage is in the details</p><h2 id="member-value-title">A clearer path from information to action.</h2>
      <div className="member-value-grid">
        <article><span>01 / RESEARCH</span><h3>Start with the game.</h3><p>Scores, matchups, player context, and news give you a place to start.</p></article>
        <article><span>02 / DECIDE</span><h3>See what supports the call.</h3><p>Inspect the price, sources, and uncertainty before deciding whether to act.</p></article>
        <article><span>03 / MEASURE</span><h3>Keep results accountable.</h3><p>Winning matters. So does net ROI after costs. Prediction-market profitability is still being validated.</p><button className="member-text-button" onClick={() => onNavigate('Prediction Markets')}>See current validation <ArrowRight size={16} /></button></article>
      </div>
    </section>
    <DashboardHub onNavigate={onNavigate} embedded />
  </div>
}
