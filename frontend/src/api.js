const API = import.meta.env.VITE_API_URL ?? (window.location.port === '5173' ? `${window.location.protocol}//${window.location.hostname}:8000` : '')
async function request(path,options={}){
  const isForm=typeof FormData!=='undefined' && options.body instanceof FormData
  const headers=isForm ? {...(options.headers||{})} : {'Content-Type':'application/json',...(options.headers||{})}
  const res=await fetch(API+path,{credentials:'include',headers,...options})
  const data=await res.json().catch(()=>({}))
  if(!res.ok){
    let message=data?.message || `Request failed (${res.status})`
    if(typeof data?.detail==='string') message=data.detail
    else if(Array.isArray(data?.detail)){
      message=data.detail.map(item=>item?.msg || 'Invalid request value').join(' · ')
    }
    const err=new Error(message)
    err.status=res.status
    err.payload=data
    throw err
  }
  return data
}
export const api={
  me:()=>request('/api/auth/me'),
  demo:()=>request('/api/auth/demo',{method:'POST'}),
  login:body=>request('/api/auth/login',{method:'POST',body:JSON.stringify(body)}),
  register:body=>request('/api/auth/register',{method:'POST',body:JSON.stringify(body)}),
  logout:()=>request('/api/auth/logout',{method:'POST'}),
  consent:()=>request('/api/auth/consent',{method:'POST',body:JSON.stringify({accepted:true})}),
  movies:()=>request('/api/movies'),
  searchMovies:q=>request(`/api/catalogue/search?q=${encodeURIComponent(q)}&limit=24`),
  siteHero:()=>request('/api/site/hero'),
  chat:body=>request('/api/chat',{method:'POST',body:JSON.stringify(body)}),
  compare:body=>request('/api/compare',{method:'POST',body:JSON.stringify(body)}),
  similar:body=>request('/api/similar',{method:'POST',body:JSON.stringify(body)}),
  tournamentSignal:body=>request('/api/compare/tournament-signal',{method:'POST',body:JSON.stringify(body)}),
  plan:body=>request('/api/plan',{method:'POST',body:JSON.stringify(body)}),
  flag:body=>request('/api/feedback',{method:'POST',body:JSON.stringify(body)}),
  watched:body=>request('/api/watch-events',{method:'POST',body:JSON.stringify(body)}),
  fairness:()=>request('/api/fairness'),
  traces:()=>request('/api/traces?limit=80'),
  savePlan:(title,plan)=>request('/api/plans/save',{method:'POST',body:JSON.stringify({title,plan})}),
  plans:()=>request('/api/plans'),
  profiles:()=>request('/api/family/profiles'),
  createProfile:body=>request('/api/family/profiles',{method:'POST',body:JSON.stringify(typeof body==='string'?{name:body}:body)}),
  updateProfile:(id,body)=>request(`/api/family/profiles/${id}`,{method:'PUT',body:JSON.stringify(body)}),
  profilePreferences:id=>request(`/api/family/profiles/${id}/preferences`),
  profileHistory:id=>request(`/api/family/profiles/${id}/history`),
  deleteProfile:id=>request(`/api/family/profiles/${id}`,{method:'DELETE'}),
  switchProfile:profile_id=>request('/api/family/profiles/switch',{method:'POST',body:JSON.stringify({profile_id})}),
  groupChoice:body=>request('/api/family/group-choice',{method:'POST',body:JSON.stringify(body)}),
  createGroup:body=>request('/api/family/groups',{method:'POST',body:JSON.stringify(body)}),
  groupRecommend:id=>request(`/api/family/groups/${id}/recommend`,{method:'POST'}),
  groupCompare:(id,movie_ids)=>request(`/api/family/groups/${id}/compare`,{method:'POST',body:JSON.stringify({movie_ids})}),
  groupVote:(id,profile_id,movie_id)=>request(`/api/family/groups/${id}/vote`,{method:'POST',body:JSON.stringify({profile_id,movie_id})}),
  groupResult:id=>request(`/api/family/groups/${id}/result`),
  groupSession:id=>request(`/api/family/groups/${id}`),
  billingStatus:()=>request('/api/billing/status'),
  paymentProfile:()=>request('/api/billing/payment-profile'),
  savePaymentProfile:body=>request('/api/billing/payment-profile',{method:'PUT',body:JSON.stringify(body)}),
  deletePaymentProfile:()=>request('/api/billing/payment-profile',{method:'DELETE'}),
  simulateSubscribe:plan=>request('/api/billing/simulate-subscribe',{method:'POST',body:JSON.stringify({plan})}),
  simulateCancel:()=>request('/api/billing/simulate-cancel',{method:'POST'}),
  checkout:plan=>request('/api/billing/checkout',{method:'POST',body:JSON.stringify({plan})}),
  cancelSubscription:()=>request('/api/billing/cancel',{method:'POST'}),
  summarize:movie_id=>request('/api/movies/summarize',{method:'POST',body:JSON.stringify({movie_id,max_sentences:3})}),
  moodCheck:body=>request('/api/planner/mood-check',{method:'POST',body:JSON.stringify(body)}),
  plannerInsights:()=>request('/api/planner/insights'),
  weeklySummary:()=>request('/api/planner/weekly-summary'),
  calendarStatus:()=>request('/api/calendar/status'),
  connectLocalCalendar:()=>request('/api/calendar/connect',{method:'POST',body:JSON.stringify({provider:'local'})}),
  disconnectCalendar:()=>request('/api/calendar/disconnect',{method:'POST'}),
  googleCalendarConnect:()=>request('/api/calendar/google/connect'),
  calendarBusySlots:()=>request('/api/calendar/busy-slots'),
  addCalendarBusySlot:body=>request('/api/calendar/busy-slots',{method:'POST',body:JSON.stringify(body)}),
  deleteCalendarBusySlot:id=>request(`/api/calendar/busy-slots/${id}`,{method:'DELETE'}),
  calendarFreeWindows:body=>request('/api/calendar/free-windows',{method:'POST',body:JSON.stringify(body)}),
  addPlanToCalendar:body=>request('/api/calendar/add-plan',{method:'POST',body:JSON.stringify(body)}),
  adminOverview:()=>request('/api/admin/overview'),
  adminImportPopular:(pages=5)=>request(`/api/admin/catalogue/import-popular?pages=${pages}`,{method:'POST'}),
  adminEnrichProducers:(limit=120)=>request(`/api/admin/catalogue/enrich-producers?limit=${limit}`,{method:'POST'}),
  adminMovies:q=>request(`/api/admin/movies?q=${encodeURIComponent(q||'')}&limit=120`),
  adminUpdateMovie:(id,body)=>request(`/api/admin/movies/${id}`,{method:'PUT',body:JSON.stringify(body)}),
  adminUploadMovieImage:(id,kind,file)=>request(`/api/admin/movies/${id}/image?kind=${kind}`,{method:'POST',headers:{'Content-Type':file.type},body:file}),
  adminUsers:()=>request('/api/admin/users?limit=120'),
  adminSecurity:()=>request('/api/admin/security/assessment'),
  adminSecurityEvents:()=>request('/api/admin/security-events?limit=100'),

}
