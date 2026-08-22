import { DocumentDetailPanel } from "./DocumentDetailPanel";

interface PageProps {
  params: {
    id: string;
  };
}

export default function DocumentDetailPage({ params }: PageProps) {
  return <DocumentDetailPanel documentId={params.id} />;
}
