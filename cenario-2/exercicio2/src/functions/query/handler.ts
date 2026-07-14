import { app, type HttpRequest, type HttpResponseInit, type InvocationContext } from "@azure/functions";

import { ValidationError } from "../../shared/errors";
import { mapZodIssuesToDetails, queryRequestSchema } from "./validator";

interface ValidationErrorResponseBody {
  error: "validation_error";
  details: Array<{
    code: string;
    message: string;
    path: (string | number)[];
  }>;
}

const jsonValidationResponse = (details: ValidationErrorResponseBody["details"]): HttpResponseInit => ({
  status: 400,
  jsonBody: {
    error: "validation_error",
    details,
  } satisfies ValidationErrorResponseBody,
});

const hasJsonContentType = (request: HttpRequest): boolean => {
  const contentType = request.headers.get("content-type");

  return typeof contentType === "string" && contentType.toLowerCase().includes("application/json");
};

const parseRequestBody = async (request: HttpRequest): Promise<unknown> => {
  if (!hasJsonContentType(request)) {
    throw new ValidationError("Content-Type must be application/json");
  }

  try {
    return await request.json();
  } catch {
    throw new ValidationError("Request body must be valid JSON");
  }
};

export const queryHandler = async (request: HttpRequest, _context: InvocationContext): Promise<HttpResponseInit> => {
  try {
    const requestBody = await parseRequestBody(request);
    const parsedRequest = queryRequestSchema.safeParse(requestBody);

    if (!parsedRequest.success) {
      return jsonValidationResponse(mapZodIssuesToDetails(parsedRequest.error.issues));
    }

    return {
      status: 501,
      jsonBody: {
        error: "not_implemented",
        message: "Query orchestration is not implemented yet.",
      },
    };
  } catch (error: unknown) {
    if (error instanceof ValidationError) {
      return jsonValidationResponse([
        {
          code: "invalid_request",
          message: error.message,
          path: [],
        },
      ]);
    }

    throw error;
  }
};

app.http("query", {
  methods: ["POST"],
  authLevel: "anonymous",
  route: "query",
  handler: queryHandler,
});