package prompt

import (
	"bytes"
	"strings"
	"testing"

	"github.com/yukihito-jokyu/context/cli/internal/project"
	"github.com/yukihito-jokyu/context/cli/internal/session"
)

func TestFormatProjectNotFound(t *testing.T) {
	tests := []struct {
		name        string
		projectName string
		suggestions []string
		wantParts   []string
	}{
		{
			name:        "returns simple error without suggestions",
			projectName: "missing",
			wantParts:   []string{"project not found: missing"},
		},
		{
			name:        "returns suggestions",
			projectName: "sprng",
			suggestions: []string{"spring-batch", "spring-boot-api"},
			wantParts:   []string{"project not found: sprng", "Did you mean?", "spring-batch", "spring-boot-api"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := FormatProjectNotFound(tt.projectName, tt.suggestions)
			for _, part := range tt.wantParts {
				if !strings.Contains(err.Error(), part) {
					t.Fatalf("expected %q in %q", part, err.Error())
				}
			}
		})
	}
}

func TestPrintSessionStarted(t *testing.T) {
	tests := []struct {
		name    string
		session session.DeploySession
		want    []string
	}{
		{
			name: "prints session summary",
			session: session.DeploySession{
				ContextRoot:           "/tmp/context",
				ContextRootResolvedBy: "cwd-parent-search",
				Project:               project.Project{Name: "context", Path: "/tmp/context/projects/context"},
				TargetDir:             "/work/target",
				SharedSkillsAvailable: true,
				CompleteContextRoot:   true,
				TargetIsGitRepository: false,
			},
			want: []string{
				"Deploy session started",
				"context root: /tmp/context",
				"project: context",
				"shared skills available: true",
				"git repository: false",
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var out bytes.Buffer
			if err := PrintSessionStarted(&out, &tt.session); err != nil {
				t.Fatalf("PrintSessionStarted returned error: %v", err)
			}
			for _, part := range tt.want {
				if !strings.Contains(out.String(), part) {
					t.Fatalf("expected %q in %q", part, out.String())
				}
			}
		})
	}
}
