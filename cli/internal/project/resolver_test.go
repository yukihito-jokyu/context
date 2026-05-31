package project

import (
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/yukihito-jokyu/context/cli/internal/errs"
)

func TestListProjects(t *testing.T) {
	tests := []struct {
		name        string
		setup       func(*testing.T) string
		wantNames   []string
		wantErrText string
	}{
		{
			name: "lists directories in sorted order",
			setup: func(t *testing.T) string {
				dir := t.TempDir()
				for _, name := range []string{"zeta", "alpha"} {
					if err := os.Mkdir(filepath.Join(dir, name), 0o755); err != nil {
						t.Fatalf("failed to create project: %v", err)
					}
				}
				if err := os.WriteFile(filepath.Join(dir, "README.md"), []byte("ignore"), 0o644); err != nil {
					t.Fatalf("failed to create file: %v", err)
				}
				return dir
			},
			wantNames: []string{"alpha", "zeta"},
		},
		{
			name: "returns error when projects dir cannot be read",
			setup: func(t *testing.T) string {
				dir := t.TempDir()
				file := filepath.Join(dir, "projects.txt")
				if err := os.WriteFile(file, []byte("not a dir"), 0o644); err != nil {
					t.Fatalf("failed to create file: %v", err)
				}
				return file
			},
			wantErrText: "failed to read projects dir",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			projects, err := List(tt.setup(t))
			if tt.wantErrText == "" && err != nil {
				t.Fatalf("List returned error: %v", err)
			}
			if tt.wantErrText != "" {
				if err == nil || !strings.Contains(err.Error(), tt.wantErrText) {
					t.Fatalf("expected error containing %q, got %v", tt.wantErrText, err)
				}
				return
			}

			var names []string
			for _, p := range projects {
				names = append(names, p.Name)
			}
			if !reflect.DeepEqual(names, tt.wantNames) {
				t.Fatalf("unexpected projects: %#v", names)
			}
		})
	}
}

func TestResolveProject(t *testing.T) {
	tests := []struct {
		name      string
		setup     func(*testing.T) string
		project   string
		wantPath  string
		wantFound bool
		wantErrIs error
	}{
		{
			name: "returns existing project",
			setup: func(t *testing.T) string {
				dir := t.TempDir()
				if err := os.Mkdir(filepath.Join(dir, "context"), 0o755); err != nil {
					t.Fatalf("failed to create project: %v", err)
				}
				return dir
			},
			project:   "context",
			wantPath:  "context",
			wantFound: true,
		},
		{
			name: "returns not found when project missing",
			setup: func(t *testing.T) string {
				return t.TempDir()
			},
			project: "context",
		},
		{
			name: "returns not found when path is file",
			setup: func(t *testing.T) string {
				dir := t.TempDir()
				if err := os.WriteFile(filepath.Join(dir, "context"), []byte("file"), 0o644); err != nil {
					t.Fatalf("failed to create file: %v", err)
				}
				return dir
			},
			project: "context",
		},
		{
			name: "rejects path traversal",
			setup: func(t *testing.T) string {
				return t.TempDir()
			},
			project:   "../context",
			wantErrIs: errs.ErrInvalidProjectName,
		},
		{
			name: "rejects dot",
			setup: func(t *testing.T) string {
				return t.TempDir()
			},
			project:   ".",
			wantErrIs: errs.ErrInvalidProjectName,
		},
		{
			name: "rejects empty name",
			setup: func(t *testing.T) string {
				return t.TempDir()
			},
			project:   "",
			wantErrIs: errs.ErrInvalidProjectName,
		},
		{
			name: "rejects nested path",
			setup: func(t *testing.T) string {
				return t.TempDir()
			},
			project:   filepath.Join("context", "cli"),
			wantErrIs: errs.ErrInvalidProjectName,
		},
		{
			name: "rejects double dot",
			setup: func(t *testing.T) string {
				return t.TempDir()
			},
			project:   "..",
			wantErrIs: errs.ErrInvalidProjectName,
		},
		{
			name: "returns stat failure",
			setup: func(t *testing.T) string {
				originalStatProjectPath := statProjectPath
				statProjectPath = func(string) (os.FileInfo, error) { return nil, os.ErrPermission }
				t.Cleanup(func() {
					statProjectPath = originalStatProjectPath
				})
				return t.TempDir()
			},
			project: "context",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dir := tt.setup(t)
			project, err := Resolve(dir, tt.project)
			if tt.wantFound {
				if err != nil {
					t.Fatalf("Resolve returned error: %v", err)
				}
				wantPath := filepath.Join(dir, tt.wantPath)
				if project.Path != wantPath {
					t.Fatalf("expected project path %q, got %q", wantPath, project.Path)
				}
				return
			}

			if tt.wantErrIs != nil {
				if !errors.Is(err, tt.wantErrIs) {
					t.Fatalf("expected error %v, got %v", tt.wantErrIs, err)
				}
				return
			}
			if err != nil && strings.Contains(err.Error(), "failed to stat project") {
				return
			}

			var notFound errs.ProjectNotFoundError
			if !errors.As(err, &notFound) {
				t.Fatalf("expected ProjectNotFoundError, got %v", err)
			}
		})
	}
}

func TestSuggestProjects(t *testing.T) {
	projects := []Project{
		{Name: "spring-batch"},
		{Name: "spring-boot-api"},
		{Name: "context"},
		{Name: "grasp-planning"},
	}

	tests := []struct {
		name     string
		projects []Project
		query    string
		limit    int
		want     []string
	}{
		{
			name:     "prioritizes prefix matches",
			projects: projects,
			query:    "spring",
			limit:    3,
			want:     []string{"spring-batch", "spring-boot-api", "context"},
		},
		{
			name:     "caps limit at project count",
			projects: projects,
			query:    "",
			limit:    10,
			want:     []string{"context", "spring-batch", "grasp-planning", "spring-boot-api"},
		},
		{
			name:     "supports contains match ordering",
			projects: projects,
			query:    "plan",
			limit:    2,
			want:     []string{"grasp-planning", "context"},
		},
		{
			name:     "returns empty when limit is zero",
			projects: projects,
			query:    "spring",
			limit:    0,
			want:     []string{},
		},
		{
			name: "breaks score ties alphabetically",
			projects: []Project{
				{Name: "bcd"},
				{Name: "abd"},
			},
			query: "acd",
			limit: 2,
			want:  []string{"abd", "bcd"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := Suggest(tt.projects, tt.query, tt.limit)
			if !reflect.DeepEqual(got, tt.want) {
				t.Fatalf("expected %v, got %v", tt.want, got)
			}
		})
	}
}

func TestNotFoundErrorError(t *testing.T) {
	err := errs.ProjectNotFoundError{Name: "context"}
	if got := err.Error(); got != "project not found: context" {
		t.Fatalf("unexpected error message: %q", got)
	}
}

func TestInvalidNameErrorError(t *testing.T) {
	err := errs.InvalidProjectNameError{Name: "../context"}
	if got := err.Error(); got != "invalid project name: ../context" {
		t.Fatalf("unexpected error message: %q", got)
	}
}

func TestInvalidNameErrorUnwrap(t *testing.T) {
	err := errs.InvalidProjectNameError{Name: "../context"}
	if !errors.Is(err, errs.ErrInvalidProjectName) {
		t.Fatalf("expected wrapped invalid project name error, got %v", err)
	}
}

func TestIsValidProjectName(t *testing.T) {
	tests := []struct {
		name    string
		project string
		want    bool
	}{
		{name: "valid", project: "context", want: true},
		{name: "empty", project: "", want: false},
		{name: "dot", project: ".", want: false},
		{name: "double dot", project: "..", want: false},
		{name: "nested", project: "context/cli", want: false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := isValidProjectName(tt.project); got != tt.want {
				t.Fatalf("expected %t, got %t", tt.want, got)
			}
		})
	}
}

func TestLevenshtein(t *testing.T) {
	tests := []struct {
		name string
		a    string
		b    string
		want int
	}{
		{name: "same strings", a: "context", b: "context", want: 0},
		{name: "empty left", a: "", b: "context", want: 7},
		{name: "empty right", a: "context", b: "", want: 7},
		{name: "edit distance", a: "kitten", b: "sitting", want: 3},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := levenshtein(tt.a, tt.b); got != tt.want {
				t.Fatalf("expected %d, got %d", tt.want, got)
			}
		})
	}
}
