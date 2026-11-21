export async function api<T=unknown>(path:string, options:RequestInit={}):Promise<T> {
  let response:Response;
  try{response=await fetch('/api'+path,{...options,credentials:'same-origin',headers:{...(options.body instanceof FormData?{}:{'Content-Type':'application/json'}),...options.headers}})}catch{throw new Error('Koneksi ke server SIPAK terputus. Pastikan server berjalan lalu coba kembali.')}
  if(!response.ok){
    const error=await response.json().catch(()=>null);
    const detail=error?.detail;
    const featureRoute=path==='/settings/letterhead'||path==='/evaluation/articles'||/\/evaluation\/draft$/.test(path);
    if(response.status===404&&featureRoute&&(!detail||detail==='Not Found'))throw new Error('Fitur ini belum tersedia pada server yang aktif. Muat ulang server SIPAK agar memakai versi terbaru.');
    if(typeof detail==='string')throw new Error(detail);
    if(Array.isArray(detail))throw new Error(detail.map(item=>item.msg||'Isian tidak valid.').join(' '));
    if(response.status===401)throw new Error('Sesi berakhir. Silakan masuk kembali.');
    if([502,503,504].includes(response.status))throw new Error('Server SIPAK belum tersedia atau melewati batas waktu. Coba kembali setelah server aktif.');
    throw new Error('Permintaan belum berhasil diproses oleh server SIPAK. Coba kembali.');
  }
  try{return await response.json()}catch{throw new Error('Respons server SIPAK tidak valid. Muat ulang server dan coba kembali.')}
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
