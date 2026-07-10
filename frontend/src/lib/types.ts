/**
 * TypeScript types matching FastAPI Pydantic models for student/teacher API.
 */

export interface ChatMessage {
  role: string;
  content: string;
}

export interface PipelineScores {
  entailment: boolean;
  consistency: boolean;
  confidence: number;
  fallback_type?: string;
}

export interface BlueprintStudentRequest {
  question: string;
  doc_ids: string[];
  chat_history?: ChatMessage[];
}

export interface BlueprintStudentResponse {
  text: string;
  entailment: boolean;
  consistency: boolean;
  confidence: number;
  fallback_type: string;
  source_used?: string;
  source_reference?: string | null;
  scores?: PipelineScores;
}

export interface BlueprintTeacherRequest {
  question: string;
  doc_ids: string[];
  chat_history?: ChatMessage[];
  context?: string;
}

export interface BlueprintTeacherResponse {
  text: string;
  entailment: boolean;
  consistency: boolean;
  confidence: number;
  fallback_type: string;
  source_used?: string;
  source_reference?: string | null;
  scores?: PipelineScores;
}

export type QuizQuestionType = "mcq" | "fill" | "code" | "math";

export interface QuizQuestion {
  level: number;
  type: QuizQuestionType;
  q: string;
  code?: string;
  options?: string[];
  answer: string | string[];
  explain: string;
}

export interface DocumentUploadRequest {
  filename: string;
  content: string;
  owner_role: string;
}

export interface DocumentUploadResponse {
  doc_id: string;
  filename: string;
  chunk_count: number;
}

export interface DocumentItem {
  id: string;
  filename: string;
  owner_role: string;
  uploaded_at: string;
}

export interface DocumentListResponse {
  documents: DocumentItem[];
}

export interface PointGrade {
  point: string;
  score: number;
  passed: boolean;
  needs_review: boolean;
}

export interface FlaggedGradeItem {
  grade_id: string;
  student_answer: string;
  overall_score: number;
  rubric_breakdown: PointGrade[];
  created_at: string;
}

export interface FlaggedGradesResponse {
  flagged_grades: FlaggedGradeItem[];
}
