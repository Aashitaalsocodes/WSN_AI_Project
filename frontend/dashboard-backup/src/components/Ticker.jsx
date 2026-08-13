import React from 'react'

export default function Ticker({ text }) {
  return (
    <div className="ticker-bar">
      <div className="ticker-track">
        <span className="ticker-content">{text}</span>
        <span className="ticker-content">{text}</span>
      </div>
    </div>
  )
}
