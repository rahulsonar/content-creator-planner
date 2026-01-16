-- CreateEnum
CREATE TYPE "ConversationStatus" AS ENUM ('IN_PROGRESS', 'COMPLETED', 'FAILED');

-- CreateTable
CREATE TABLE "ContextManagerConversation" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "conversationId" TEXT,
    "agentName" TEXT NOT NULL DEFAULT 'context_manager',
    "userMessage" TEXT NOT NULL,
    "assistantMessage" TEXT,
    "toolCalls" JSONB,
    "toolResults" JSONB,
    "metadata" JSONB,
    "status" "ConversationStatus" NOT NULL DEFAULT 'COMPLETED',
    "errorMessage" TEXT,
    "startedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "ContextManagerConversation_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "ContextManagerConversation_userId_idx" ON "ContextManagerConversation"("userId");

-- CreateIndex
CREATE INDEX "ContextManagerConversation_conversationId_idx" ON "ContextManagerConversation"("conversationId");

-- CreateIndex
CREATE INDEX "ContextManagerConversation_agentName_idx" ON "ContextManagerConversation"("agentName");

-- CreateIndex
CREATE INDEX "ContextManagerConversation_startedAt_idx" ON "ContextManagerConversation"("startedAt");
