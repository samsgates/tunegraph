import { Nav } from "@/components/nav";
import { api } from "@/lib/api";

type Patch = { id:string; state:string };
type Graph = { id:string; state:string };
type Deployment = { id:string; state:string };

export default async function Dashboard() {
  const [patches, graphs, deployments] = await Promise.all([
    api<Patch[]>("/api/v1/patches"),
    api<Graph[]>("/api/v1/graphs"),
    api<Deployment[]>("/api/v1/deployments")
  ]);
  return <div className="shell"><Nav/><main><h1>Behavior operations</h1><p className="muted">Current organization inventory and deployment posture.</p><div className="grid"><div className="card">Patch releases<div className="metric">{patches.length}</div></div><div className="card">Graph releases<div className="metric">{graphs.length}</div></div><div className="card">Deployments<div className="metric">{deployments.length}</div></div><div className="card">Production patches<div className="metric">{patches.filter(p=>p.state==="production").length}</div></div></div></main></div>;
}
