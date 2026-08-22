import { PageContainer } from "@/components/layout/PageContainer";
import { CourseWorkspace } from "./CourseWorkspace";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function CourseWorkspacePage({ params }: PageProps) {
  const { id } = await params;
  return (
    <PageContainer>
      <CourseWorkspace courseId={id} />
    </PageContainer>
  );
}
