export type DocumentRole = "textbook" | "sample_exam";
export type PdfScope = "chapter" | "full";
export type DocumentStatus =
  | "uploaded"
  | "parsed"
  | "extracted"
  | "failed";

export interface DocumentInfo {
  id: number;
  file_name: string;
  original_name: string;
  subject: string;
  document_role: DocumentRole;
  pdf_scope: PdfScope;
  chapter_outline: Array<{
    title: string;
    start_page: number;
    end_page: number;
    page_label?: string | null;
    level?: number;
    key?: string;
    parent_key?: string | null;
  }> | null;
  status: DocumentStatus;
  page_count: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  documents: DocumentInfo[];
  total: number;
}

export interface QuestionInfo {
  id: number;
  source_document_id: number;
  source_role: string;
  subject: string | null;
  chapter: string | null;
  page_start: number | null;
  page_end: number | null;
  question_number: string | null;
  question_text: string;
  tags: string[] | null;
  figure_refs: Array<{
    id: string;
    page_number: number;
    url: string;
    path?: string;
    bbox?: number[];
    label?: string | null;
    caption?: string | null;
  }> | null;
  extracted_confidence: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface QuestionListResponse {
  questions: QuestionInfo[];
  total: number;
}

export interface QuestionFilterOptionsResponse {
  subjects: string[];
  chapters: string[];
  chapters_by_subject: Record<string, string[]>;
}

export interface QuestionTranslationResponse {
  question_id: number;
  translated_text: string;
}
