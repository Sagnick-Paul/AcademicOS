import { PageContainer } from "@/components/layout/PageContainer";
import { EmptyState } from "@/components/primitives/EmptyState";

export default function DashboardPage() {
  return (
    <PageContainer>
      <EmptyState
        title="Dashboard is coming in a later phase"
        description="Today it just exists to prove routing and the application shell work end-to-end."
      />
    </PageContainer>
  );
}
