import { Hero } from "@/components/marketing/hero";
import { ProblemCards } from "@/components/marketing/problem-cards";
import { PipelineDiagram } from "@/components/marketing/pipeline-diagram";
import { GateCards } from "@/components/marketing/gate-cards";
import { RecallProof } from "@/components/marketing/recall-proof";
import { LocalFirst } from "@/components/marketing/local-first";
import { IdentityPreview } from "@/components/marketing/identity-preview";
import { TerminalTabs } from "@/components/marketing/terminal-tabs";
import { CTA } from "@/components/marketing/cta";

export default function HomeExplicitPage() {
  return (
    <div>
      <Hero />
      <ProblemCards />
      <PipelineDiagram />
      <GateCards />
      <RecallProof />
      <LocalFirst />
      <IdentityPreview />
      <TerminalTabs />
      <CTA />
    </div>
  );
}
