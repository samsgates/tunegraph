import { Nav } from "@/components/nav";
import { api } from "@/lib/api";
type Deployment = { id:string; name:string; environment:string; state:string; traffic_percentage:number; graph_release_id:string };
export default async function Page(){ const items=await api<Deployment[]>("/api/v1/deployments"); return <div className="shell"><Nav/><main><h1>Deployments</h1><p className="muted">Canary, production, and rollback status.</p><table><thead><tr><th>Name</th><th>Environment</th><th>Traffic</th><th>Graph</th><th>State</th></tr></thead><tbody>{items.map(x=><tr key={x.id}><td>{x.name}</td><td>{x.environment}</td><td>{x.traffic_percentage}%</td><td>{x.graph_release_id.slice(0,8)}</td><td><span className="status">{x.state}</span></td></tr>)}</tbody></table></main></div> }
