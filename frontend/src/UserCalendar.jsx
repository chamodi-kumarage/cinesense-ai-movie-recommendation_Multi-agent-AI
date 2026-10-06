import React, { useEffect, useMemo, useState } from 'react'

export function localDateKey(date) {
  return [date.getFullYear(), String(date.getMonth()+1).padStart(2,'0'), String(date.getDate()).padStart(2,'0')].join('-')
}

function dateFromKey(key) {
  const [year,month,day]=key.split('-').map(Number)
  return new Date(year,month-1,day)
}

function eventsOnDay(events,date) {
  const start=new Date(date.getFullYear(),date.getMonth(),date.getDate())
  const end=new Date(date.getFullYear(),date.getMonth(),date.getDate()+1)
  return events.filter(event=>new Date(event.start_at)<end&&new Date(event.end_at)>start)
}

export default function UserCalendar({events,selectedDate,onSelect,onRemove,loading,error,busy,onRefresh}) {
  const [month,setMonth]=useState(()=>new Date(new Date().getFullYear(),new Date().getMonth(),1))
  useEffect(()=>{
    const date=dateFromKey(selectedDate)
    setMonth(new Date(date.getFullYear(),date.getMonth(),1))
  },[selectedDate])
  const today=localDateKey(new Date())
  const days=useMemo(()=>{
    const first=new Date(month.getFullYear(),month.getMonth(),1)
    const offset=(first.getDay()+6)%7
    return Array.from({length:42},(_,index)=>new Date(first.getFullYear(),first.getMonth(),index-offset+1))
  },[month])
  const agenda=eventsOnDay(events,dateFromKey(selectedDate)).sort((a,b)=>new Date(a.start_at)-new Date(b.start_at))
  const moveMonth=step=>setMonth(current=>new Date(current.getFullYear(),current.getMonth()+step,1))
  const goToday=()=>{
    const now=new Date()
    setMonth(new Date(now.getFullYear(),now.getMonth(),1))
    onSelect(localDateKey(now))
  }
  const formatTime=value=>new Date(value).toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})
  return <section className="user-calendar">
    <div className="user-calendar-heading">
      <div><h3>Your marked calendar</h3><p>Busy times and watch plans saved to your account. Select a day to view or add events.</p></div>
      <button className="btn-secondary" disabled={loading} onClick={onRefresh}>{loading?'Loading...':'Refresh events'}</button>
    </div>
    <div className="calendar-month-navigation">
      <button className="btn-secondary" aria-label="Previous month" onClick={()=>moveMonth(-1)}>Previous</button>
      <h4 aria-live="polite">{month.toLocaleDateString([], {month:'long',year:'numeric'})}</h4>
      <button className="btn-secondary" aria-label="Next month" onClick={()=>moveMonth(1)}>Next</button>
      <button className="btn-secondary" onClick={goToday}>Today</button>
    </div>
    <div className="calendar-event-legend"><span><i className="busy-dot"/>Busy time</span><span><i className="plan-dot"/>Watch plan</span><span>Timezone: {Intl.DateTimeFormat().resolvedOptions().timeZone}</span></div>
    {error&&<div role="alert" className="error-box">{error}</div>}
    <div className="user-calendar-weekdays" aria-hidden="true">{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map(day=><span key={day}>{day}</span>)}</div>
    <div className="user-calendar-days" aria-label="Month calendar" aria-busy={loading}>
      {days.map(date=>{
        const key=localDateKey(date)
        const dayEvents=eventsOnDay(events,date)
        return <button type="button" key={key} className={'calendar-day'+(date.getMonth()!==month.getMonth()?' outside-month':'')+(key===selectedDate?' selected-day':'')+(key===today?' today-day':'')} aria-pressed={key===selectedDate} aria-label={date.toLocaleDateString([], {weekday:'long',year:'numeric',month:'long',day:'numeric'})+', '+dayEvents.length+' saved events'} onClick={()=>onSelect(key)}>
          <span className="calendar-day-number">{date.getDate()}{key===today&&<small>Today</small>}</span>
          <span className="calendar-day-events">{dayEvents.slice(0,2).map(event=><span className={'calendar-event-chip '+(event.source==='watch-plan'?'watch-plan':'busy-time')} key={event.id} title={event.title}>{event.title}</span>)}{dayEvents.length>2&&<small>+{dayEvents.length-2} more</small>}</span>
        </button>
      })}
    </div>
    <div className="calendar-day-agenda">
      <h4>{dateFromKey(selectedDate).toLocaleDateString([], {weekday:'long',month:'long',day:'numeric',year:'numeric'})}</h4>
      {!loading&&!error&&!agenda.length&&<p>No saved events on this day. Add a busy time below or add a watch plan from the planner.</p>}
      {agenda.map(event=><div className="calendar-agenda-event" key={event.id}>
        <div><span className={'calendar-event-type '+(event.source==='watch-plan'?'watch-plan':'busy-time')}>{event.source==='watch-plan'?'Watch plan':'Busy time'}</span><strong>{event.title}</strong><small>{formatTime(event.start_at)} - {formatTime(event.end_at)}</small></div>
        <button className="btn-secondary" disabled={busy} onClick={()=>onRemove(event.id)}>Remove event</button>
      </div>)}
    </div>
  </section>
}
