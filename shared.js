
/* ---------- Data layer: every read and write goes to the central cloud API (nothing is stored in the browser) ---------- */
const API=((window.APP_CONFIG&&window.APP_CONFIG.API_BASE)||"").replace(/\/$/,"");
let STATE={students:[],complaints:[],session:null,adminSession:null};
const load=()=>STATE;
const save=()=>{};
function httpHint(c){
  if(c===404||c===405)return `Can't reach the backend API (HTTP ${c}). Open the site through the Flask server (python app.py, then http://127.0.0.1:5000/admin), not Live Server or a static-only host.`;
  if(c===500)return "The server hit an error (HTTP 500). Check the server terminal or the cloud logs for the cause.";
  if(c>=502&&c<=504)return `The server is not responding (HTTP ${c}). On a free cloud plan it may be waking up. Wait a minute and try again.`;
  return `Request failed (HTTP ${c}).`;
}
async function api(path,body){
  try{
    const r=await fetch(API+path,{method:"POST",headers:{"Content-Type":"application/json"},credentials:"include",body:JSON.stringify(body||{})});
    const d=await r.json().catch(()=>null);
    return r.ok?{ok:true,...(d||{})}:{ok:false,error:(d&&d.error)||httpHint(r.status)};
  }catch(e){return {ok:false,error:"Can't reach the server. Check your internet connection and that the server is running."};}
}
async function refresh(){   // PORTAL ("student" or "admin") is set by each page's script
  try{const r=await fetch(API+"/api/state?as="+PORTAL,{credentials:"include"});if(r.ok)STATE=await r.json();}catch(e){}
}
function toast(m){const t=document.createElement("div");t.className="toast";t.textContent=m;document.body.appendChild(t);setTimeout(()=>t.remove(),3500);}
/* Automatic updates: every 8 seconds ask the server "did anything change?" and redraw if so (never while someone is typing). */
const busy=()=>{const d=$("desc"),p=$("prev"),a=document.activeElement;
  return !!document.querySelector(".modal")||!!(d&&d.value)||!!(p&&p.children.length)||!!(a&&/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)&&a.type!=="checkbox");};
let lastV=null;
async function tick(){
  if(document.hidden)return;
  try{
    const r=await fetch(API+"/api/ping?as="+PORTAL,{credentials:"include"});if(!r.ok)return;
    const v=(await r.json()).v;
    if(lastV===null){lastV=v;return;}
    if(v!==lastV&&!busy()){
      const before=STATE.complaints.length;await refresh();show();lastV=v;
      if(PORTAL==="admin"&&STATE.complaints.length>before)toast("New complaint received");
    }
  }catch(e){}
}
function startPolling(){tick();setInterval(tick,8000);}

/* Hostel structure: hostel -> wing -> floor -> rooms (replace with a rooms table in a real backend) */
const WINGS=["A","B","C"], FLOORS=[0,1,2,3,4,5,6,7,8];
const floorName=f=>f===0?"Ground":f+(["st","nd","rd"][f-1]||"th");
/* Rooms depend on the wing: A = 1-4, B = 5-10, C = 11-16, D = 17-24, E = 25-32 (with the floor in front, e.g. floor 2 wing B = 205-210) */
const WING_ROOMS={A:[1,4],B:[5,10],C:[11,16],D:[17,24],E:[25,32]};
const roomsOn=(f,w)=>{const [a,b]=WING_ROOMS[w]||[1,50];return Array.from({length:b-a+1},(_,i)=>{const n=String(a+i).padStart(2,"0");return f===0?"G"+n:f+n;});};
const CATEGORIES=["Water","Wi-Fi","Electrical","Cleanliness","Furniture","Other"];
const ICON={Water:"💧","Wi-Fi":"📶",Electrical:"⚡",Cleanliness:"🧹",Furniture:"🪑",Other:"📝"};

const esc=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const $=id=>document.getElementById(id);
const app=$("app");


const profileLine=s=>`${s.hostel} • ${s.wing} Wing • ${floorName(s.floor)} Floor • Room ${s.room}`;



/* Hostels and their wings (edit to match your campus) */
const HOSTELS={H1:["A","B","C","D","E"],H2:["A","B","C","D","E"]};
/* Hostel council. Put photos in the images/ folder and set photo:"images/h1-gensec.jpg".
   Leave photo empty to show a placeholder icon. */
const COUNCIL={
  H1:[
    {name:"Ram Mittal",role:"H1 Secretary",email:"ch25bt008@iitdh.ac.in",photo:(window.PHOTOS||{}).h1secretary||"images/h1-secretary.jpg",featured:true},
    {name:"Add name here",role:"Warden",photo:""},
    {name:"Add name here",role:"General Secretary",photo:""},
    {name:"Add name here",role:"Maintenance Secretary",photo:""},
    {name:"Add name here",role:"Mess Secretary",photo:""},
    {name:"Add name here",role:"Cultural Secretary",photo:""},
    {name:"Add name here",role:"Sports Secretary",photo:""}
  ],
  H2:[
    {name:"Siddarth Shukla",role:"H2 Secretary",email:"is24bm039@iitdh.ac.in",photo:(window.PHOTOS||{}).h2secretary||"images/h2-secretary.jpg",featured:true},
    {name:"Add name here",role:"Warden",photo:""},
    {name:"Add name here",role:"General Secretary",photo:""},
    {name:"Add name here",role:"Maintenance Secretary",photo:""},
    {name:"Add name here",role:"Mess Secretary",photo:""},
    {name:"Add name here",role:"Cultural Secretary",photo:""},
    {name:"Add name here",role:"Sports Secretary",photo:""}
  ]
};
