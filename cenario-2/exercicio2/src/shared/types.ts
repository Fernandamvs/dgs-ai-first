export interface ConversationTurn {
  role: "user" | "assistant";
  content: string;
}

export interface QueryRequest {
  question: string;
  conversationHistory?: ConversationTurn[];
}

export interface Chunk {
  id: string;
  content: string;
  sourceDocument: string;
  score: number;
  vigencia: "vigente" | "obsoleto";
}

export interface QueryResponse {
  answer: string;
  sourceDocuments: string[];
}