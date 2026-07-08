import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";

// Dense pack model — keep in sync with tools/lschain/prepare.py max_segments_per_page
const SEG = 64;
function cborUintLen(n){ return n<24?1:n<256?2:n<65536?3:n<4294967296?5:9; }
function cborBytesLen(n){ return cborUintLen(n)+n; }
function estimatePageTxBytes(segs, nPages=999){
  let inner = cborUintLen(5);
  inner += 2 + cborUintLen(1);
  inner += 2 + cborUintLen(Math.max(1,nPages));
  inner += 2 + cborUintLen(segs) + segs*cborBytesLen(SEG);
  inner += 4 + cborBytesLen(32);
  inner += 2 + cborUintLen(2);
  const outer = cborUintLen(1) + cborUintLen(22025) + inner;
  const aux = 3 + cborUintLen(1) + cborUintLen(0) + outer;
  return 1 + 120 + 110 + 1 + aux;
}
function maxSegmentsPerPage(maxTx=16384, safety=400){
  const budget = Math.max(1024, maxTx - safety);
  let lo=1, hi=400, best=190;
  while(lo<=hi){
    const mid=(lo+hi)>>1;
    if(estimatePageTxBytes(mid) <= budget){ best=mid; lo=mid+1; }
    else hi=mid-1;
  }
  return best;
}

const BND_SEG=SEG, BND_SPP=maxSegmentsPerPage(), BND_PAGE=BND_SEG*BND_SPP;
const bHex=u8=>Buffer.from(u8).toString("hex");
const sha=u8=>createHash("sha256").update(u8).digest("hex");
const bytes=new Uint8Array(readFileSync("sample.bin"));
const n=Math.max(1,Math.ceil(bytes.length/BND_PAGE)); const pageShas=[];
for(let i=0;i<n;i++){
  const payload=bytes.subarray(i*BND_PAGE,Math.min((i+1)*BND_PAGE,bytes.length));
  const s=sha(payload); pageShas.push(s);
  const segs=[]; for(let o=0;o<payload.length;o+=BND_SEG) segs.push("0x"+bHex(payload.subarray(o,Math.min(o+BND_SEG,payload.length))));
  writeFileSync(`js-page-${String(i+1).padStart(4,"0")}.json`, JSON.stringify({"22025":{v:2,i:i+1,n,sha:"0x"+s,p:segs}}));
}
const plan={format:"ls-chain-v2-plan",sourceFile:"sample.bin",contentType:"application/octet-stream",codec:"none",
  sizeDecoded:bytes.length,sizeEncoded:bytes.length,sha256Decoded:sha(bytes),sha256Encoded:sha(bytes),
  pages:n,segmentBytes:BND_SEG,segmentsPerPage:BND_SPP,pagePayloadBytes:BND_PAGE,
  estimatedPageTxBytes:estimatePageTxBytes(BND_SPP,n),
  pageSha256:pageShas,metadataLabel:22025};
writeFileSync("js-plan.json", JSON.stringify(plan,null,2)+"\n");
console.log("js pages:",n,"segs/page:",BND_SPP,"payload:",BND_PAGE);
