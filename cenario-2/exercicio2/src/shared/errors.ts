export type ExternalServiceName = "azure-openai" | "azure-search";

interface ErrorPayload {
  error: string;
  message: string;
}

export class ValidationError extends Error {
  public readonly statusCode = 400;

  public constructor(message: string) {
    super(message);
    this.name = "ValidationError";
    Object.setPrototypeOf(this, new.target.prototype);
  }

  public toJSON(): ErrorPayload {
    return {
      error: "validation_error",
      message: this.message,
    };
  }
}

export class ExternalServiceError extends Error {
  public readonly statusCode = 502;
  public readonly serviceName: ExternalServiceName;

  public constructor(serviceName: ExternalServiceName, message: string) {
    super(message);
    this.name = "ExternalServiceError";
    this.serviceName = serviceName;
    Object.setPrototypeOf(this, new.target.prototype);
  }

  public toJSON(): ErrorPayload {
    return {
      error: this.serviceName,
      message: this.message,
    };
  }
}

export class RetryExhaustedError extends ExternalServiceError {
  public readonly statusCode = 503;
  public readonly attempts: number;

  public constructor(serviceName: ExternalServiceName, attempts: number) {
    super(serviceName, `Retry exhausted for ${serviceName} after ${attempts} attempts.`);
    this.name = "RetryExhaustedError";
    this.attempts = attempts;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}