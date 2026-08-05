import { Nav } from "@/components/nav";
import { api } from "@/lib/api";
type Patch = { id:string; family:string; version:number; state:string; risk_tier:string; rank:number };
export default async function Page(){ const items=await api<Patch[]>("/api/v1/patches"); return <div className="shell"><Nav/><main><h1>Patches</h1><p className="muted">Immutable behavior releases.</p><table><thead><tr><th>Family</th><th>Version</th><th>Rank</th><th>Risk</th><th>State</th></tr></thead><tbody>{items.map(x=><tr key={x.id}><td>{x.family}</td><td>v{x.version}</td><td>{x.rank}</td><td>{x.risk_tier}</td><td><span className="status">{x.state}</span></td></tr>)}</tbody></table></main></div> }
