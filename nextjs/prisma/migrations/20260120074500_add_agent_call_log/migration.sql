-- CreateEnum
CREATE TYPE "AgentCallStatus" AS ENUM ('IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED');

-- CreateTable
CREATE TABLE "AgentCallLog" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "conversationId" TEXT,
    "messageId" TEXT NOT NULL,
    "sessionId" TEXT,
    "agentName" TEXT NOT NULL,
    "agentType" TEXT,
    "agentVersion" TEXT,
    "modelName" TEXT NOT NULL,
    "modelProvider" TEXT NOT NULL DEFAULT 'openai',
    "inputMessage" TEXT,
    "outputMessage" TEXT,
    "toolsEnabled" BOOLEAN NOT NULL DEFAULT false,
    "toolCalls" JSONB,
    "toolResults" JSONB,
    "status" "AgentCallStatus" NOT NULL DEFAULT 'IN_PROGRESS',
    "startedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completedAt" TIMESTAMP(3),
    "durationMs" INTEGER,
    "promptTokens" INTEGER,
    "completionTokens" INTEGER,
    "totalTokens" INTEGER,
    "error" TEXT,
    "errorType" TEXT,
    "stackTrace" TEXT,
    "metadata" JSONB,
    "tags" TEXT[],
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "AgentCallLog_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "AgentCallLog_userId_idx" ON "AgentCallLog"("userId");

-- CreateIndex
CREATE INDEX "AgentCallLog_conversationId_idx" ON "AgentCallLog"("conversationId");

-- CreateIndex
CREATE INDEX "AgentCallLog_messageId_idx" ON "AgentCallLog"("messageId");

-- CreateIndex
CREATE INDEX "AgentCallLog_agentName_idx" ON "AgentCallLog"("agentName");

-- CreateIndex
CREATE INDEX "AgentCallLog_status_idx" ON "AgentCallLog"("status");

-- CreateIndex
CREATE INDEX "AgentCallLog_startedAt_idx" ON "AgentCallLog"("startedAt");

-- CreateIndex
CREATE INDEX "AgentCallLog_sessionId_idx" ON "AgentCallLog"("sessionId");
