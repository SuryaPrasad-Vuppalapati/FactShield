/**
 * Typed API client for calling FactShield backend routes.
 */

import type {
  BlueprintStudentRequest,
  BlueprintStudentResponse,
  BlueprintTeacherRequest,
  BlueprintTeacherResponse,
  DocumentUploadResponse,
  DocumentListResponse,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

async function post<T, U>(endpoint: string, data: T): Promise<U> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    headers,
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
  const headers: Record<string, string> = {
    "Accept": "application/json",
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "GET",
    headers,
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
  // STUDENT FEATURES
  async conceptGuide(req: BlueprintStudentRequest): Promise<BlueprintStudentResponse> {
    return post<BlueprintStudentRequest, BlueprintStudentResponse>("/student/concept-guide", req);
  },

  async problemNavigator(req: BlueprintStudentRequest): Promise<BlueprintStudentResponse> {
    return post<BlueprintStudentRequest, BlueprintStudentResponse>("/student/problem-navigator", req);
  },

  async submissionValidator(req: BlueprintStudentRequest): Promise<BlueprintStudentResponse> {
    return post<BlueprintStudentRequest, BlueprintStudentResponse>("/student/submission-validator", req);
  },

  async quizGenerator(req: BlueprintStudentRequest): Promise<BlueprintStudentResponse> {
    return post<BlueprintStudentRequest, BlueprintStudentResponse>("/student/quiz-generator", req);
  },

  // TEACHER FEATURES
  async assignmentGrader(req: BlueprintTeacherRequest): Promise<BlueprintTeacherResponse> {
    return post<BlueprintTeacherRequest, BlueprintTeacherResponse>("/teacher/assignment-grader", req);
  },

  async examGenerator(req: BlueprintTeacherRequest): Promise<BlueprintTeacherResponse> {
    return post<BlueprintTeacherRequest, BlueprintTeacherResponse>("/teacher/exam-generator", req);
  },

  async adaptiveFeedback(req: BlueprintTeacherRequest): Promise<BlueprintTeacherResponse> {
    return post<BlueprintTeacherRequest, BlueprintTeacherResponse>("/teacher/adaptive-feedback", req);
  },

  async learningInsights(req: BlueprintTeacherRequest): Promise<BlueprintTeacherResponse> {
    return post<BlueprintTeacherRequest, BlueprintTeacherResponse>("/teacher/learning-insights", req);
  },

  // DOCUMENT MANAGEMENT
  async uploadDocument(file: File, ownerRole: string = "student"): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("owner_role", ownerRole);

    const response = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Upload failed");
    }
    return response.json();
  },

  async listDocuments(): Promise<DocumentListResponse> {
    return get<DocumentListResponse>("/documents/");
  },

  async deleteDocument(doc_id: string): Promise<any> {
    return fetch(`${API_BASE_URL}/documents/${doc_id}`, { method: "DELETE" }).then(res => res.json());
  },

  async extractText(file: File): Promise<{ text: string }> {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`${API_BASE_URL}/documents/extract`, { method: "POST", body: formData }).then(res => res.json());
  },

  async getFlaggedGrades(): Promise<any> {
    return get<any>("/teacher/flagged-grades");
  }
};
