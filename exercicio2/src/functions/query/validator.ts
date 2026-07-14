import { z, type ZodIssue } from "zod";

import { ValidationError } from "../../shared/errors";
import type { ConversationTurn, QueryRequest } from "../../shared/types";

export const conversationTurnSchema: z.ZodType<ConversationTurn> = z.object({
  role: z.enum(["user", "assistant"]),
  content: z.string(),
});

export const queryRequestSchema: z.ZodType<QueryRequest> = z.object({
  question: z.string().min(1).max(2000),
  conversationHistory: z.array(conversationTurnSchema).max(3).optional(),
});

export interface ValidationIssueDetail {
  code: string;
  message: string;
  path: (string | number)[];
}

export const mapZodIssuesToDetails = (issues: ZodIssue[]): ValidationIssueDetail[] =>
  issues.map((issue) => ({
    code: issue.code,
    message: issue.message,
    path: issue.path,
  }));

export const validateQueryRequest = (input: unknown): QueryRequest => {
  const parsed = queryRequestSchema.safeParse(input);

  if (!parsed.success) {
    const details = mapZodIssuesToDetails(parsed.error.issues);
    const detailsString = JSON.stringify(details);

    throw new ValidationError(`Invalid query request: ${detailsString}`);
  }

  return parsed.data;
};