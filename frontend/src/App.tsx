import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Overview from "./pages/Overview";
import Predictions from "./pages/Predictions";
import Incidents from "./pages/Incidents";
import GraphView from "./pages/GraphView";
import Impact from "./pages/Impact";
import Audit from "./pages/Audit";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/predictions" element={<Predictions />} />
        <Route path="/incidents" element={<Incidents />} />
        <Route path="/graph" element={<GraphView />} />
        <Route path="/impact" element={<Impact />} />
        <Route path="/audit" element={<Audit />} />
      </Routes>
    </Layout>
  );
}
