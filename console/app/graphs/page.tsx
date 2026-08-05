import { Nav } from "@/components/nav";
import { api } from "@/lib/api";
type Graph = { id:string; name:string; version:number; state:string; patch_ids:string[]; policy_revision:string };
export default async function Page(){ const items=await api<Graph[]>("/api/v1/graphs"); return <div className="shell"><Nav/><main><h1>Capability graphs</h1><p className="muted">Signed patch compositions and policy snapshots.</p><table><thead><tr><th>Name</th><th>Version</th><th>Patches</th><th>Policy</th><th>State</th></tr></thead><tbody>{items.map(x=><tr key={x.id}><td>{x.name}</td><td>v{x.version}</td><td>{x.patch_ids.length}</td><td>{x.policy_revision}</td><td><span className="status">{x.state}</span></td></tr>)}</tbody></table></main></div> }
