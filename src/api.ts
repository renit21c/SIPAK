export async function api<T=unknown>(path:string, options:RequestInit={}):Promise<T> {
  const response=await fetch('/api'+path,{...options,credentials:'same-origin',headers:{...(options.body instanceof FormData?{}:{'Content-Type':'application/json'}),...options.headers}});
  if(!response.ok){
    const error=await response.json().catch(()=>({detail:'Server tidak dapat dihubungi.'}));
    throw new Error(typeof error.detail==='string'?error.detail:JSON.stringify(error.detail));
  }
  return response.json();
}
export const post=<T=unknown>(path:string,data:unknown={})=>api<T>(path,{method:'POST',body:JSON.stringify(data)});
export function upload(path:string, data:FormData, progress?:(value:number)=>void):Promise<unknown> {
  return new Promise((resolve,reject)=>{
    const xhr=new XMLHttpRequest(); xhr.open('POST','/api'+path); xhr.withCredentials=true;
    xhr.upload.onprogress=e=>{if(e.lengthComputable)progress?.(Math.round(e.loaded/e.total*100))};
    xhr.onload=()=>{let data;try{data=JSON.parse(xhr.responseText)}catch{reject(new Error('Respons server tidak valid.'));return}
      if(xhr.status>=200&&xhr.status<300)resolve(data);else reject(new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail)))};
    xhr.onerror=()=>reject(new Error('Koneksi terputus. Periksa server SIPAK.')); xhr.send(data);
  });
}
