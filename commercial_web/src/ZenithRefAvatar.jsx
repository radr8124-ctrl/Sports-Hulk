import React from 'react'

/** Original Sports Zenith referee-inspired AI mascot, not an NFL or league official. */
export default function ZenithRefAvatar({size=64,compact=false,className=''}) {
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" role="img"
      aria-label="Zenith AI referee avatar" className={className}>
      <title>Zenith's Ref — sports intelligence assistant</title>
      <defs>
        <linearGradient id="zref-frame" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#2FC8FA"/><stop offset=".46" stopColor="#0D4E89"/>
          <stop offset="1" stopColor="#13243B"/>
        </linearGradient>
        <linearGradient id="zref-visor" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#21BBEE"/><stop offset="1" stopColor="#0A78BD"/>
        </linearGradient>
        <clipPath id="zref-clip"><circle cx="60" cy="60" r="53"/></clipPath>
      </defs>
      <circle cx="60" cy="60" r="59" fill="#04101F"/>
      <circle cx="60" cy="60" r="57" fill="none" stroke="url(#zref-frame)" strokeWidth="2.5"/>
      <g clipPath="url(#zref-clip)">
        <circle cx="60" cy="61" r="52" fill="#0A1B30"/>
        <path d="M-1 87 32 63 60 58 90 65 122 87 122 123-1 123Z" fill="#07111E"/>
        <path d="M27 81 47 71 47 117 26 121Z" fill="#E5F7FF"/>
        <path d="M36 75 42 73 42 120 36 120Z" fill="#081423"/>
        <path d="M50 72 60 76 69 72 69 120 50 120Z" fill="#E8F6FF"/>
        <path d="M55 75 62 76 62 120 55 120Z" fill="#09182B"/>
        <path d="M76 72 83 75 90 121 74 120Z" fill="#EBFAFF"/>
        <path d="M80 74 84 76 91 120 86 120Z" fill="#0B1A2B"/>
        <path d="M38 39c0-17 10-26 23-26s23 9 23 26v14c0 15-9 26-23 26S38 68 38 53Z"
          fill="#172D45" stroke="#34607B" strokeWidth="2"/>
        <path d="M36 40c2-17 11-29 26-29s25 12 26 29l-4 6-48-1Z" fill="#0C1728"/>
        <path d="M35 38c6-20 22-27 37-21 9 4 14 11 16 21" fill="none" stroke="#A5C6D9" strokeWidth="3"/>
        <path d="M37 43 84 43 78 59 42 59Z" fill="#071525" stroke="#55BCE9" strokeWidth="2"/>
        <path d="M44 45 78 45 73 50 47 50Z" fill="url(#zref-visor)" opacity=".94"/>
        <path d="M52 67q9 6 18 0" fill="none" stroke="#7BB4D0" strokeWidth="2.5" strokeLinecap="round"/>
        <rect x="32" y="42" width="7" height="17" rx="3" fill="#1981C1" stroke="#B4E8FC"/>
        <path d="M34 55c0 17 12 23 22 25" fill="none" stroke="#21B7E9" strokeWidth="3" strokeLinecap="round"/>
        <circle cx="55" cy="80" r="3.1" fill="#28C7F8"/>
        <path d="M91 20 100 31 95 40" fill="none" stroke="#29B5E5" strokeWidth="2.5" strokeLinecap="round"/>
        <rect x="46" y="90" width="29" height="21" rx="6" fill="#072942" stroke="#36C5F5" strokeWidth="1.6"/>
        <text x="60.5" y="105.5" fontFamily="system-ui,sans-serif" fontWeight="900" fontSize="14"
          fill="#DFFAFF" textAnchor="middle">Z</text>
        {!compact && <g transform="translate(83 82) rotate(-19)">
          <rect x="0" y="0" width="14" height="7" rx="3.5" fill="#B9DCEA" stroke="#0B2942"/>
          <circle cx="4" cy="8" r="3.6" fill="#2CC4F3" stroke="#B9EEFF"/>
        </g>}
      </g>
      <circle cx="60" cy="60" r="53" fill="none" stroke="#42BBE6" strokeOpacity=".44" strokeWidth="1"/>
    </svg>
  )
}
