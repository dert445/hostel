const PORTAL="student";
let view="home", councilHostel=null;
const nav=cur=>`<div class="nav"><button data-nav="home" class="${cur==="home"?"on":""}">My complaints</button><button data-nav="council" class="${cur==="council"?"on":""}">Hostel council</button></div>`;
app.addEventListener("click",e=>{const b=e.target.closest("[data-nav]");if(b){view=b.dataset.nav;if(view==="council")councilHostel="H1";show();}});
const avatar=m=>m.photo?`<div class="avatar"><img src="${esc(m.photo)}" alt="${esc(m.name)}" onerror="this.parentNode.remove()"></div>`:"";
const named=m=>m.name&&m.name!=="Add name here";
const shown=h=>COUNCIL[h].filter(m=>named(m)||m.photo); // hide unfilled placeholder members
function councilView(st){
  const h=councilHostel||"H1";   // H1 always comes first; the H1/H2 switch changes it
  app.innerHTML=nav("council")+`<h1>Hostel Council</h1><p class="sub">The people who look after your hostel.</p>
  <div class="seg">${Object.keys(HOSTELS).map(x=>`<button class="${x===h?"on":""}" data-h="${x}">${x}</button>`).join("")}</div>
  <div class="council">${shown(h).length?shown(h).map(m=>`<div class="member${m.featured?" featured":""}">${avatar(m)}<div class="mi">${named(m)?`<b>${esc(m.name)}</b>`:""}<span>${esc(m.role)}</span>${m.featured?`<em>${m.email?`<a href="mailto:${esc(m.email)}">${esc(m.email)}</a>`:`${h} HOSTEL`}</em><p class="quote">“Here to make hostel life better.”</p>`:""}</div></div>`).join(""):`<p class="empty" style="grid-column:1/-1">Council details for ${h} will be added soon.</p>`}</div>`;
  app.querySelectorAll("[data-h]").forEach(b=>b.onclick=()=>{councilHostel=b.dataset.h;show();});
}
function show(){
  const db=load(), s=db.session;
  $("logout").classList.toggle("hide",!s);
  $("hero").classList.toggle("hide",!!s);
  if(!s) return loginView();
  const st=db.students.find(x=>x.id===s.id);
  if(!st){db.session=null;save();return loginView();}
  return view==="council"?councilView(st):dashboardView(st);
}
function loginView(msg=""){
  app.innerHTML=`<div class="card"><h1>Log in</h1><p class="sub">Welcome back. Log in with your institute email.</p>
  <label for="le">Institute email</label><input id="le" type="email" autocomplete="username" placeholder="rollno@iitdh.ac.in">
  <label for="lp">Password</label><input id="lp" type="password" autocomplete="current-password">
  ${msg}<div id="lerr"></div>
  <button class="btn" id="lbtn">Log in</button>
  <p class="hint">New here? <button class="link" id="goreg">Create an account</button></p>
</div>`;
  $("goreg").onclick=registerView;
  $("lbtn").onclick=async()=>{
    const r=await api("/api/login",{email:$("le").value.trim().toLowerCase(),password:$("lp").value});
    if(!r.ok){$("lerr").innerHTML=`<div class="msg err">${esc(r.error)}</div>`;return;}
    await refresh();show();
  };
}

function registerView(){
  app.innerHTML=`<div class="card"><h1>Student registration</h1><p class="sub">Sign up with your institute email (rollno@iitdh.ac.in). Your account is ready right away.</p>
  <label for="name">Full name</label><input id="name" autocomplete="name">
  <label for="hostel">Hostel</label><select id="hostel"></select>
  <div class="row"><div><label for="wing">Wing</label><select id="wing"></select></div>
  <div><label for="floor">Floor</label><select id="floor"></select></div></div>
  <label for="room">Room number</label><select id="room"></select>
  <label for="wa">WhatsApp number</label><input id="wa" type="tel" inputmode="numeric" autocomplete="tel" placeholder="10-digit number">
  <label for="email">Institute email</label><input id="email" type="email" autocomplete="username" placeholder="rollno@iitdh.ac.in">
  <label for="pw">Password (min 8 characters)</label><input id="pw" type="password" autocomplete="new-password">
  <div id="rerr"></div>
  <button class="btn" id="rbtn">Create account</button>
  <p class="hint">Already registered? <button class="link" id="golog">Log in</button></p></div>`;
  const wing=$("wing"),floor=$("floor"),room=$("room");
  const hostel=$("hostel");
  hostel.innerHTML=`<option value="">Select</option>`+Object.keys(HOSTELS).map(h=>`<option>${h}</option>`).join("");
  wing.innerHTML=`<option value="">Select hostel first</option>`;wing.disabled=true;
  hostel.onchange=()=>{wing.disabled=!hostel.value;
    wing.innerHTML=hostel.value?`<option value="">Select</option>`+HOSTELS[hostel.value].map(w=>`<option>${w}</option>`).join(""):`<option value="">Select hostel first</option>`;
    wing.onchange();};
  floor.innerHTML=`<option value="">Select wing first</option>`;floor.disabled=true;
  room.innerHTML=`<option value="">Select floor first</option>`;room.disabled=true;
  wing.onchange=()=>{ // wing -> floors
    floor.disabled=!wing.value;
    floor.innerHTML=wing.value?`<option value="">Select</option>`+FLOORS.map(f=>`<option value="${f}">${floorName(f)}</option>`).join(""):`<option value="">Select wing first</option>`;
    room.innerHTML=`<option value="">Select floor first</option>`;room.disabled=true;
  };
  floor.onchange=()=>{ // floor -> rooms on that floor only
    room.disabled=floor.value==="";
    room.innerHTML=floor.value===""?`<option value="">Select floor first</option>`:`<option value="">Select</option>`+roomsOn(+floor.value,wing.value).map(r=>`<option>${r}</option>`).join("");
  };
  $("golog").onclick=()=>loginView();
  $("rbtn").onclick=async()=>{
    const err=m=>{$("rerr").innerHTML=`<div class="msg err">${m}</div>`};
    const name=$("name").value.trim(), email=$("email").value.trim().toLowerCase(), pw=$("pw").value;
    if(!name) return err("Enter your full name.");
    if(!hostel.value||!wing.value||floor.value===""||!room.value) return err("Choose your hostel, wing, floor and room.");
    const wa=$("wa").value.replace(/[\s-]/g,"").replace(/^(\+91|91|0)(?=\d{10}$)/,"");
    if(!/^[6-9]\d{9}$/.test(wa)) return err("Enter a valid 10-digit WhatsApp number.");
    if(!/^[a-z0-9]{5,12}@iitdh\.ac\.in$/.test(email)) return err("Use your institute email in the form rollno@iitdh.ac.in.");
    const roll=email.split("@")[0].toUpperCase();
    if(pw.length<8) return err("Password must be at least 8 characters.");
    const r=await api("/api/register",{name,email,password:pw,whatsapp:"+91"+wa,hostel:hostel.value,wing:wing.value,floor:+floor.value,room:room.value});
    if(!r.ok) return err(esc(r.error));
    await refresh();show();
  };
}

let flash="";
const shrink=f=>new Promise((ok,no)=>{const r=new FileReader();r.onerror=no;r.onload=()=>{const im=new Image();im.onerror=no;im.onload=()=>{
  const k=Math.min(1,1280/Math.max(im.width,im.height)),c=document.createElement("canvas");c.width=Math.round(im.width*k);c.height=Math.round(im.height*k);
  c.getContext("2d").drawImage(im,0,0,c.width,c.height);ok(c.toDataURL("image/jpeg",.8));};im.src=r.result;};r.readAsDataURL(f);});
const photos=c=>(c.images||[]).length?`<div class="thumbs">${c.images.map(i=>`<a href="${API}/api/images/${i}" target="_blank" rel="noopener"><img src="${API}/api/images/${i}" alt="Attached photo" loading="lazy"></a>`).join("")}</div>`:"";
function dashboardView(st){
  const db=load(), mine=[...db.complaints].sort((a,b)=>b.n-a.n);
  const pending=mine.filter(c=>c.status!=="Resolved"&&c.status!=="Rejected").length, done=mine.filter(c=>c.status==="Resolved").length;
  const banner=flash?`<div class="msg ok" role="status">${esc(flash)}</div>`:"";flash="";
  app.innerHTML=nav("home")+`<h1>Hello, ${esc(st.name.split(" ")[0])} 👋</h1><p class="sub" style="margin-bottom:0">${esc(st.email)}</p>
  <div class="profile"><span class="ph">${esc(st.hostel)} HOSTEL</span><b>${esc(st.wing)} Wing • ${floorName(st.floor)} Floor • Room ${esc(st.room)}</b></div>${banner}
  <div class="stats"><div class="stat"><b>${mine.length}</b><span>Total</span></div><div class="stat"><b>${pending}</b><span>Open</span></div><div class="stat"><b>${done}</b><span>Resolved</span></div></div>
  <div class="card"><h1 style="font-size:1.15rem">Report a problem</h1><p class="sub" style="margin:0">Tell us what needs attention.</p>
  <label for="cat">Category</label><select id="cat">${CATEGORIES.map(c=>`<option>${c}</option>`).join("")}</select>
  <label for="desc">What's the problem?</label><textarea id="desc" rows="3" maxlength="500"></textarea>
  <label for="pics">Photos (optional, up to 3)</label><input id="pics" type="file" accept="image/*" multiple>
  <div id="prev" class="thumbs"></div><div id="cerr"></div><button class="btn" id="cbtn">Submit Complaint →</button></div>
  <h2>Recent complaints</h2><div class="card list">${mine.length?mine.map(c=>`
  <div class="item"><span class="ico">${ICON[c.category]||"📝"}</span><div class="grow"><b>${esc(c.code)}</b> · ${esc(c.category)} <span class="prio P-${esc(c.priority)}">${esc(c.priority)}</span>
  <small>${esc(c.description)}</small>${c.assignedTo?`<small>Assigned to: ${esc(c.assignedTo)}</small>`:""}${c.remarks?`<small>${c.status==="Rejected"?"Reason":"Update from secretary"}: ${esc(c.remarks)}</small>`:""}${photos(c)}
  <small class="date">Submitted ${new Date(c.createdAt).toLocaleString()}${c.status==="Resolved"&&c.resolvedAt?` · Resolved ${new Date(c.resolvedAt).toLocaleString()}`:""}</small></div>
  <div class="side"><span class="tag ${c.status.replace(" ","-")}">${c.status}</span>${c.status==="Rejected"?"":`<label class="tick"><input type="checkbox" data-r="${c.n}"${c.status==="Resolved"?" checked":""}> Resolved</label>`}</div></div>`).join(""):'<p class="empty">No complaints yet. Use the form above to report your first problem.</p>'}</div>`;
  let pics=[];
  $("pics").onchange=async e=>{
    try{pics=[];for(const f of [...e.target.files].slice(0,3))pics.push(await shrink(f));$("prev").innerHTML=pics.map(p=>`<img src="${p}" alt="Selected photo">`).join("");$("cerr").innerHTML="";}
    catch(x){pics=[];$("prev").innerHTML="";$("cerr").innerHTML='<div class="msg err">One of the photos could not be read.</div>';}
  };
  app.querySelectorAll("[data-r]").forEach(cb=>cb.onchange=async()=>{
    await api("/api/complaints/"+cb.dataset.r+"/resolve",{resolved:cb.checked});await refresh();show();
  });
  $("cbtn").onclick=async()=>{
    const d=$("desc").value.trim();
    if(d.length<10){$("cerr").innerHTML='<div class="msg err">Describe the problem in at least 10 characters.</div>';return;}
    $("cbtn").disabled=true;
    const r=await api("/api/complaints",{category:$("cat").value,description:d,images:pics});
    if(!r.ok){$("cbtn").disabled=false;$("cerr").innerHTML=`<div class="msg err">${esc(r.error)}</div>`;return;}
    flash=`Complaint submitted. Your ticket ID is ${r.code}.`;await refresh();show();
  };
}


$("logout").onclick=async()=>{view="home";await api("/api/logout");await refresh();show();};
// pick up secretary decisions when the tab regains focus (don't wipe a half-written complaint)
window.addEventListener("focus",async()=>{const d=$("desc");if(load().session&&!(d&&d.value)){await refresh();show();}});
refresh().then(()=>{show();startPolling();});
