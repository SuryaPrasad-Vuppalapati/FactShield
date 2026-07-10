with open("frontend/src/lib/api.ts", "r") as f:
    content = f.read()

# I messed up the file with the previous replace. I will rewrite api.ts correctly.
import re

new_content = """/**
 * Typed API client for calling FactShield backend routes.
 */

import type {
  BestScoredSummaryRequest,
  BestScoredSummaryResponse,
  ChallengeBackRequest,
  ChallengeBackResponse,
  ConceptExplainerRequest,
  DocumentUploadResponse,
  DocumentListResponse,
  FlaggedGradesResponse,
  GradeAnswerRequest,
  GradeAnswerResponse,
  MethodGroundingRequest,
  MethodGroundingResponse,
  SelfCheckRequest,
  SelfCheckResponse,
  SourceHunterRequest,
  SourceHunterResponse,
  TestGeneratorRequest,
  TestGeneratorResponse,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

async function post<T, U>(endpoint: string, data: T): Promise<U> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    let errorMsg = `API error: ${response.status} ${response.statusText}`;
    try {
      const errBody = await response.json();
      if (errBody.response) errorMsg = errBody.response;
      else if (errBody.detail) errorMsg = errBody.detail;
    } catch (e) {
      // Ignore JSON parse errors
    }
    throw new Error(errorMsg);
  }

  return response.json() as Promise<U>;
}

async function get<U>(endpoint: string): Promise<U> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "GET",
    headers: {
      "Accept": "application/json",
    },
  });

  if (!response.ok) {
    let errorMsg = `API error: ${response.status} ${response.statusText}`;
    try {
      const errBody = await response.json();
      if (errBody.response) errorMsg = errBody.response;
      else if (errBody.detail) errorMsg = errBody.detail;
    } catch (e) {
      // Ignore JSON parse errors
    }
    throw new Error(errorMsg);
  }

  return response.json() as Promise<U>;
}

export const api = {
  /**
   * Request grounded technique passages from student material.
   */
  async methodGrounding(req: MethodGroundingRequest): Promise<MethodGroundingResponse> {
    return post<MethodGroundingRequest, MethodGroundingResponse>("/student/method-grounding", req);
  },

  /**
   * Submit student answer for open-ended rubric grading.
   */
  async gradeAnswer(req: GradeAnswerRequest): Promise<GradeAnswerResponse> {
    return post<GradeAnswerRequest, GradeAnswerResponse>("/teacher/grade-answer", req);
  },

  /**
   * Upload and index a document.
   */
  async uploadDocument(file: File, ownerRole: string = "student"): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("owner_role", ownerRole);

    const response = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    return response.json() as Promise<DocumentUploadResponse>;
  },

  /**
   * Submit student's explanation to check it against source definitions.
   */
  async challengeBack(req: ChallengeBackRequest): Promise<ChallengeBackResponse> {
    return post<ChallengeBackRequest, ChallengeBackResponse>("/student/challenge-back", req);
  },

  /**
   * Perform sentence-level self check on student's writing.
   */
  async selfCheck(req: SelfCheckRequest): Promise<SelfCheckResponse> {
    return post<SelfCheckRequest, SelfCheckResponse>("/student/self-check", req);
  },

  /**
   * Locate matching passage in documents for student claim.
   */
  async sourceHunter(req: SourceHunterRequest): Promise<SourceHunterResponse> {
    return post<SourceHunterRequest, SourceHunterResponse>("/student/source-hunter", req);
  },

  /**
   * Generate Best-Scored Summary.
   */
  async bestScoredSummary(req: BestScoredSummaryRequest): Promise<BestScoredSummaryResponse> {
    return post<BestScoredSummaryRequest, BestScoredSummaryResponse>("/student/best-scored-summary", req);
  },

  /**
   * Generate high-quality explanation of concept.
   */
  async conceptExplainer(req: ConceptExplainerRequest): Promise<BestScoredSummaryResponse> {
    return post<ConceptExplainerRequest, BestScoredSummaryResponse>("/teacher/concept-explainer", req);
  },

  /**
   * Generate practice questions checked against source.
   */
  async testGenerator(req: TestGeneratorRequest): Promise<TestGeneratorResponse> {
    return post<TestGeneratorRequest, TestGeneratorResponse>("/teacher/test-generator", req);
  },

  /**
   * Fetch evaluation records flagged for review.
   */
  async getFlaggedGrades(): Promise<FlaggedGradesResponse> {
    return get<FlaggedGradesResponse>("/teacher/flagged-grades");
  },

  /**
   * Fetch list of all uploaded documents.
   */
  async listDocuments(): Promise<DocumentListResponse> {
    return get<DocumentListResponse>("/documents");
  },

  /**
   * Delete a document.
   */
  async deleteDocument(docId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/documents/${docId}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    return response.json();
  },

  /**
   * Extract text from a file.
   */
  async extractText(file: File): Promise<{ text: string; filename: string }> {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${API_BASE_URL}/documents/extract-text`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    return response.json();
  },
};
"""
with open("frontend/src/lib/api.ts", "w") as f:
    f.write(new_content)
