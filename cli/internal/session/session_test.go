package session

import (
	"testing"

	"github.com/yukihito-jokyu/context/cli/internal/filesystem"
	"github.com/yukihito-jokyu/context/cli/internal/project"
)

func TestNewSession(t *testing.T) {
	tests := []struct {
		name              string
		root              filesystem.ContextRoot
		project           project.Project
		wantSharedSkills  bool
		wantCompleteRoot  bool
		wantGitRepository bool
	}{
		{
			name: "copies available shared skills state",
			root: filesystem.ContextRoot{
				Path:               "/tmp/context",
				ResolvedBy:         "cwd-parent-search",
				Complete:           true,
				SharedSkillsExists: true,
			},
			project:           project.Project{Name: "context", Path: "/tmp/context/projects/context"},
			wantSharedSkills:  true,
			wantCompleteRoot:  true,
			wantGitRepository: true,
		},
		{
			name: "disables shared skill selection when skills are missing",
			root: filesystem.ContextRoot{
				Path:               "/tmp/context",
				ResolvedBy:         "cwd-parent-search",
				Complete:           false,
				SharedSkillsExists: false,
			},
			project:           project.Project{Name: "context", Path: "/tmp/context/projects/context"},
			wantSharedSkills:  false,
			wantCompleteRoot:  false,
			wantGitRepository: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			session := New(tt.root, &tt.project, "/work/target", true, "/work/target")

			if session.ContextRoot != tt.root.Path {
				t.Fatalf("unexpected context root: %s", session.ContextRoot)
			}
			if session.Project.Name != tt.project.Name {
				t.Fatalf("unexpected project: %s", session.Project.Name)
			}
			if session.CanSelectSharedSkills != tt.wantSharedSkills {
				t.Fatalf("expected shared skill selection=%t, got %t", tt.wantSharedSkills, session.CanSelectSharedSkills)
			}
			if session.CompleteContextRoot != tt.wantCompleteRoot {
				t.Fatalf("expected complete root=%t, got %t", tt.wantCompleteRoot, session.CompleteContextRoot)
			}
			if session.TargetIsGitRepository != tt.wantGitRepository {
				t.Fatalf("expected git repository=%t, got %t", tt.wantGitRepository, session.TargetIsGitRepository)
			}
		})
	}
}
