package skill

import (
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestCollect(t *testing.T) {
	root := t.TempDir()
	sharedDir := filepath.Join(root, "utils", "skills")
	projectDir := filepath.Join(root, "projects", "alpha", "skills")

	writeSkillDir(t, sharedDir, "shared-only", "shared")
	writeSkillDir(t, sharedDir, "override", "shared override")
	writeSkillDir(t, projectDir, "override", "project override")

	if err := os.MkdirAll(filepath.Join(sharedDir, "ignored"), 0o755); err != nil {
		t.Fatalf("failed to create ignored dir: %v", err)
	}

	got, err := Collect(sharedDir, projectDir)
	if err != nil {
		t.Fatalf("Collect returned error: %v", err)
	}

	want := []Candidate{
		{Name: "override", Source: SourceProject, SourcePath: filepath.Join(projectDir, "override")},
		{Name: "shared-only", Source: SourceShared, SourcePath: filepath.Join(sharedDir, "shared-only")},
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("unexpected candidates: %#v", got)
	}
}

func TestDeployToAgents(t *testing.T) {
	targetDir := t.TempDir()
	sourceRoot := t.TempDir()
	sourceDir := filepath.Join(sourceRoot, "override")
	writeSkillDir(t, sourceRoot, "override", "project override")

	for _, base := range []string{".claude/skills/override", ".codex/skills/override"} {
		existingDir := filepath.Join(targetDir, base)
		if err := os.MkdirAll(existingDir, 0o755); err != nil {
			t.Fatalf("failed to create existing dir: %v", err)
		}
		if err := os.WriteFile(filepath.Join(existingDir, "README.md"), []byte("old"), 0o644); err != nil {
			t.Fatalf("failed to create existing README: %v", err)
		}
	}

	err := DeployToAgents(targetDir, []Candidate{{
		Name:       "override",
		Source:     SourceProject,
		SourcePath: sourceDir,
	}})
	if err != nil {
		t.Fatalf("DeployToAgents returned error: %v", err)
	}

	for _, base := range []string{".claude/skills/override", ".codex/skills/override"} {
		skillPath := filepath.Join(targetDir, base, "SKILL.md")
		content, readErr := os.ReadFile(skillPath)
		if readErr != nil {
			t.Fatalf("failed to read deployed skill: %v", readErr)
		}
		if string(content) != "project override" {
			t.Fatalf("unexpected skill content: %q", string(content))
		}
		if _, statErr := os.Stat(filepath.Join(targetDir, base, "README.md")); !errors.Is(statErr, os.ErrNotExist) {
			t.Fatalf("expected README removal, got %v", statErr)
		}
	}
}

func writeSkillDir(t *testing.T, root, name, content string) {
	t.Helper()

	skillDir := filepath.Join(root, name)
	if err := os.MkdirAll(skillDir, 0o755); err != nil {
		t.Fatalf("failed to create skill dir: %v", err)
	}
	if err := os.WriteFile(filepath.Join(skillDir, "SKILL.md"), []byte(content), 0o644); err != nil {
		t.Fatalf("failed to create SKILL.md: %v", err)
	}
}
