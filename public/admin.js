const PORTAL="admin";
const AUTH=["Warden","Maintenance Secretary","Mess Secretary","Electrician","Plumber","Housekeeping","IT / Network","Other"];
const PRIOS=["Low","Medium","High","Urgent"], STATUSES=["Pending","In Progress","Resolved","Rejected"];
const F={q:"",hostel:"All",wing:"All",floor:"All",category:"All",status:"All"};
const fmt=iso=>iso?new Date(iso).toLocaleString([],{day:"numeric",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit"}):"";
const loc=c=>`${c.hostel} ${c.wing} Wing, ${floorName(c.floor)} floor, Room ${c.room}`;
const tagCls=s=>s.replace(" ","-");

function show(){
  const db=load();
  $("logout").classList.toggle("hide",!db.adminSession);
  $("hero").classList.toggle("hide",!!db.adminSession);
  return db.adminSession?dashboard():adminLogin();
}
function adminLogin(){
  app.innerHTML=`<div class="card"><h1>Secretary log in</h1><p class="sub">Hostel secretary access only.</p>
  <label for="ae">Email</label><input id="ae" type="email" autocomplete="username">
  <label for="ap">Password</label><input id="ap" type="password" autocomplete="current-password">
  <div id="aerr"></div><button class="btn" id="abtn">Log in</button></div>`;
  const go=async()=>{
    const r=await api("/api/admin/login",{email:$("ae").value.trim(),password:$("ap").value});
    if(!r.ok){$("aerr").innerHTML=`<div class="msg err">${esc(r.error)}</div>`;return;}
    await refresh();show();startPolling();
  };
  $("abtn").onclick=go;$("ap").onkeydown=e=>{if(e.key==="Enter")go();};
}

/* In-page dialog for the rejection reason (works everywhere, unlike prompt()) */
function askReason(done){
  const o=document.createElement("div");o.className="modal";
  o.innerHTML=`<div class="dlg card" role="dialog" aria-modal="true" aria-labelledby="rt"><h1 id="rt" style="font-size:1.25rem">Reject complaint</h1>
  <p class="sub" style="margin:0">Give a short reason. The student will see it.</p>
  <label for="rr">Reason</label><textarea id="rr" rows="3" maxlength="200" placeholder="e.g. Duplicate of an existing complaint"></textarea>
  <div id="rrerr"></div><div class="dlg-btns"><button class="act" id="rc">Cancel</button><button class="act rej" id="ro">Reject complaint</button></div></div>`;
  document.body.appendChild(o);$("rr").focus();
  const close=()=>{o.remove();document.removeEventListener("keydown",esc);};
  const esc=e=>{if(e.key==="Escape")close();};
  document.addEventListener("keydown",esc);
  $("rc").onclick=close;
  o.onclick=e=>{if(e.target===o)close();};
  $("ro").onclick=()=>{const v=$("rr").value.trim();
    if(!v){$("rrerr").innerHTML='<div class="msg err">Please enter a reason.</div>';return;}
    close();done(v);};
}

function copyNum(num){
  const say=ok=>toast((ok?"Number copied: ":"Number: ")+num);
  const fb=()=>{const t=document.createElement("textarea");t.value=num;document.body.appendChild(t);t.select();let r=false;try{r=document.execCommand("copy");}catch(e){}t.remove();say(r);};
  try{navigator.clipboard.writeText(num).then(()=>say(true),fb);}catch(e){fb();}
}
const waLink=c=>"https://wa.me/"+c.whatsapp.replace(/\D/g,"")+"?text="+encodeURIComponent("Hello "+c.studentName.split(" ")[0]+", this is the hostel secretary regarding your complaint "+c.code+".");
async function update(id,f){
  const r=await api("/api/admin/complaints/"+id,f);
  toast(r.ok?"Saved.":r.error);await refresh();show();return r.ok;
}
function quick(id,v){ if(v==="Rejected") askReason(r=>update(id,{status:v,remarks:r})); else update(id,{status:v}); }

function dashboard(){
  const scope=load().adminSession.hostel;
  const fs=(id,label,pairs)=>`<select id="f-${id}" aria-label="${label}"><option value="All">All ${label.toLowerCase()}</option>${pairs.map(([v,t])=>`<option value="${esc(v)}"${String(F[id])===String(v)?" selected":""}>${esc(t)}</option>`).join("")}</select>`;
  app.innerHTML=`<h1>Complaint Command Center</h1><p class="sub">${scope==="ALL"?"All hostels":esc(scope)+" Secretary"} · updates automatically</p>
  <div class="stats five" id="stats"></div>
  <div class="toolbar filters"><input id="q" type="search" placeholder="Search ticket, name, roll, room, text…" value="${esc(F.q)}" aria-label="Search complaints">
  ${scope==="ALL"?fs("hostel","Hostels",Object.keys(HOSTELS).map(h=>[h,h])):""}${fs("wing","Wings",["A","B","C","D","E"].map(w=>[w,"Wing "+w]))}
  ${fs("floor","Floors",FLOORS.map(f=>[f,floorName(f)+" floor"]))}${fs("category","Categories",CATEGORIES.map(c=>[c,c]))}${fs("status","Statuses",STATUSES.map(s=>[s,s]))}</div>
  <div class="card list" id="list"></div>`;
  $("q").oninput=e=>{F.q=e.target.value;paint();};
  ["hostel","wing","floor","category","status"].forEach(k=>{const el=$("f-"+k);if(el)el.onchange=e=>{F[k]=e.target.value;paint();};});
  paint();
}
function paint(){
  const all=load().complaints, n=s=>all.filter(c=>c.status===s).length, q=F.q.trim().toLowerCase();
  $("stats").innerHTML=[["Total",all.length],["Pending",n("Pending")],["In progress",n("In Progress")],["Resolved",n("Resolved")],["Rejected",n("Rejected")]].map(([l,v])=>`<div class="stat"><b>${v}</b><span>${l}</span></div>`).join("");
  const list=all.filter(c=>(F.hostel==="All"||c.hostel===F.hostel)&&(F.wing==="All"||c.wing===F.wing)&&(F.floor==="All"||String(c.floor)===F.floor)
    &&(F.category==="All"||c.category===F.category)&&(F.status==="All"||c.status===F.status)
    &&(!q||[c.code,c.studentName,c.roll,c.room,c.description,c.category,c.assignedTo||""].join(" ").toLowerCase().includes(q))).sort((a,b)=>b.n-a.n);
  $("list").innerHTML=list.length?list.map(c=>`<div class="item clickable" data-open="${c.n}" tabindex="0" role="button" aria-label="Open ${esc(c.code)}">
    <span class="ico">${ICON[c.category]||"📝"}</span><div class="grow"><b>${esc(c.code)}</b> · ${esc(c.category)} <span class="prio P-${esc(c.priority)}">${esc(c.priority)}</span>
    <small>${esc(c.description)}</small><small>${esc(c.studentName)} · ${esc(c.roll)} · ${esc(loc(c))}</small>${c.assignedTo?`<small>Assigned to ${esc(c.assignedTo)}</small>`:""}
    <small class="date">${fmt(c.createdAt)}${c.images.length?` · 📎 ${c.images.length} photo${c.images.length>1?"s":""}`:""}</small></div>
    <div class="side"><span class="tag ${tagCls(c.status)}">${c.status}</span>${c.status==="Resolved"?"":`<div class="acts">${c.status==="Rejected"?`<button class="act" data-a="Pending" data-c="${c.n}">Reopen</button>`
      :`${c.status!=="In Progress"?`<button class="act prog" data-a="In Progress" data-c="${c.n}">In Progress</button>`:`<button class="act" data-a="Pending" data-c="${c.n}">Set Pending</button>`}<button class="act rej" data-a="Rejected" data-c="${c.n}">Reject</button>`}</div>`}</div></div>`).join(""):'<p class="empty">No complaints match your search or filters.</p>';
  $("list").querySelectorAll("[data-open]").forEach(el=>{el.onclick=()=>openDetail(+el.dataset.open);el.onkeydown=e=>{if(e.key==="Enter")openDetail(+el.dataset.open);};});
  $("list").querySelectorAll("[data-a]").forEach(b=>b.onclick=e=>{e.stopPropagation();quick(b.dataset.c,b.dataset.a);});
}

function openDetail(id){
  const c=load().complaints.find(x=>x.n===id); if(!c)return;
  const o=document.createElement("div");o.className="modal";
  const opts=(arr,cur)=>arr.map(x=>`<option${x===cur?" selected":""}>${x}</option>`).join("");
  const locked=c.status==="Resolved";
  o.innerHTML=`<div class="dlg wide card" role="dialog" aria-modal="true" aria-labelledby="dt">
  <h1 id="dt" style="font-size:1.3rem">${esc(c.code)} · ${esc(c.category)}</h1>
  <span class="tag ${tagCls(c.status)}">${c.status}</span> <span class="prio P-${esc(c.priority)}">${esc(c.priority)}</span>
  <p style="margin:14px 0 8px">${esc(c.description)}</p>
  ${c.images.length?`<div class="thumbs big">${c.images.map(i=>`<a href="${API}/api/images/${i}" target="_blank" rel="noopener"><img src="${API}/api/images/${i}" alt="Complaint photo"></a>`).join("")}</div>`:""}
  <div class="detail"><div><span>Student</span>${esc(c.studentName)} (${esc(c.roll)})</div><div><span>Location</span>${esc(loc(c))}</div>
  <div><span>Submitted</span>${fmt(c.createdAt)}</div><div><span>Last updated</span>${fmt(c.updatedAt)}</div>${c.resolvedAt?`<div><span>Resolved</span>${fmt(c.resolvedAt)}</div>`:""}
  <div><span>WhatsApp</span>${esc(c.whatsapp||"")} <a id="dwa" href="${esc(waLink(c))}" target="_blank" rel="noopener noreferrer">Open</a> · <button class="link" id="dcp">Copy</button></div></div>
  <label for="d-st">Status</label><select id="d-st"${locked?" disabled":""}>${opts(locked?["Resolved"]:["Pending","In Progress","Rejected"],c.status)}</select>
  ${locked?'<small style="color:var(--mute)">The student confirmed this complaint as resolved.</small>':""}
  <div class="row"><div><label for="d-pr">Priority</label><select id="d-pr">${opts(PRIOS,c.priority)}</select></div>
  <div><label for="d-as">Assigned to</label><input id="d-as" list="auth" maxlength="60" value="${esc(c.assignedTo||"")}"><datalist id="auth">${AUTH.map(a=>`<option value="${a}">`).join("")}</datalist></div></div>
  <label for="d-rm">Remarks / resolution details (the student can see this)</label><textarea id="d-rm" rows="3" maxlength="1000">${esc(c.remarks||"")}</textarea>
  <div id="derr"></div><div class="dlg-btns"><button class="act" id="dc">Close</button><button class="btn small" id="ds">Save changes</button></div></div>`;
  document.body.appendChild(o);
  const close=()=>{o.remove();document.removeEventListener("keydown",onKey);};
  const onKey=e=>{if(e.key==="Escape")close();};document.addEventListener("keydown",onKey);
  o.onclick=e=>{if(e.target===o)close();};$("dc").onclick=close;
  $("dcp").onclick=()=>copyNum(c.whatsapp||"");
  $("ds").onclick=async()=>{
    const f={priority:$("d-pr").value,assigned_to:$("d-as").value,remarks:$("d-rm").value};
    if(!locked)f.status=$("d-st").value;
    if(f.status==="Rejected"&&!f.remarks.trim()){$("derr").innerHTML='<div class="msg err">Add a reason in the remarks when rejecting.</div>';return;}
    $("ds").disabled=true;const r=await api("/api/admin/complaints/"+id,f);
    if(!r.ok){$("ds").disabled=false;$("derr").innerHTML=`<div class="msg err">${esc(r.error)}</div>`;return;}
    close();toast("Saved.");await refresh();show();
  };
}

$("logout").onclick=async()=>{await api("/api/admin/logout");await refresh();show();};
window.addEventListener("focus",async()=>{if(load().adminSession&&!busy()){await refresh();show();}});
refresh().then(()=>{show();if(load().adminSession)startPolling();});
