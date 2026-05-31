package agents

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDeploy(t *testing.T) {
	sourceDir := t.TempDir()
	targetDir := t.TempDir()

	sourceFile := filepath.Join(sourceDir, "AGENTS.md")
	if err := os.WriteFile(sourceFile, []byte("project agents"), 0o644); err != nil {
		t.Fatalf("failed to create source AGENTS.md: %v", err)
	}

	if err := Deploy(targetDir, sourceFile); err != nil {
		t.Fatalf("Deploy returned error: %v", err)
	}

	content, err := os.ReadFile(filepath.Join(targetDir, "AGENTS.md"))
	if err != nil {
		t.Fatalf("failed to read deployed AGENTS.md: %v", err)
	}
	if string(content) != "project agents" {
		t.Fatalf("unexpected AGENTS.md content: %q", string(content))
	}
}

func TestGenerateClaude(t *testing.T) {
	sourceDir := t.TempDir()
	targetDir := t.TempDir()

	sourceFile := filepath.Join(sourceDir, "AGENTS.md")
	if err := os.WriteFile(sourceFile, []byte("project agents"), 0o644); err != nil {
		t.Fatalf("failed to create source AGENTS.md: %v", err)
	}

	if err := GenerateClaude(targetDir, sourceFile); err != nil {
		t.Fatalf("GenerateClaude returned error: %v", err)
	}

	content, err := os.ReadFile(filepath.Join(targetDir, "CLAUDE.md"))
	if err != nil {
		t.Fatalf("failed to read generated CLAUDE.md: %v", err)
	}
	if string(content) != "project agents" {
		t.Fatalf("unexpected CLAUDE.md content: %q", string(content))
	}
}
