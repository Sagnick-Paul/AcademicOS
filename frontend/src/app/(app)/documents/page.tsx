import { PageContainer } from "@/components/layout/PageContainer";
import { EmptyState } from "@/components/primitives/EmptyState";

export default function DocumentsPage() {
  return (
    <PageContainer>
      <EmptyState
        title="No documents yet"
        description="The document manager will land in Phase 4B."
      />
    </PageContainer>
  );
}
