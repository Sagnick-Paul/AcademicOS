import { PageContainer } from "@/components/layout/PageContainer";
import { EmptyState } from "@/components/primitives/EmptyState";

export default function ChatPage() {
  return (
    <PageContainer>
      <EmptyState
        title="Chat is coming soon"
        description="The grounded chat UI will land in a later phase."
      />
    </PageContainer>
  );
}
