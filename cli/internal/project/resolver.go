package project

import (
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/yukihito-jokyu/context/cli/internal/errs"
)

type Project struct {
	Name       string
	Path       string
	AgentsPath string
	ReadmePath string
	SkillsDir  string
}

var statProjectPath = os.Stat

func List(projectsDir string) ([]Project, error) {
	entries, err := os.ReadDir(projectsDir)
	if err != nil {
		return nil, errs.Wrap("failed to read projects dir", projectsDir, err)
	}

	projects := make([]Project, 0, len(entries))
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		projects = append(projects, hydrate(filepath.Join(projectsDir, entry.Name())))
	}

	sort.Slice(projects, func(i, j int) bool {
		return projects[i].Name < projects[j].Name
	})

	return projects, nil
}

func Resolve(projectsDir, name string) (Project, error) {
	if !isValidProjectName(name) {
		return Project{}, errs.InvalidProjectNameError{Name: name}
	}

	path := filepath.Join(projectsDir, name)
	info, err := statProjectPath(path)
	if err != nil {
		if os.IsNotExist(err) {
			return Project{}, errs.ProjectNotFoundError{Name: name}
		}
		return Project{}, errs.Wrap("failed to stat project", name, err)
	}
	if !info.IsDir() {
		return Project{}, errs.ProjectNotFoundError{Name: name}
	}
	return hydrate(path), nil
}

func isValidProjectName(name string) bool {
	if name == "" {
		return false
	}
	if name == "." || name == ".." {
		return false
	}
	if filepath.Base(name) != name || strings.ContainsAny(name, `/\`) {
		return false
	}
	return true
}

func Suggest(projects []Project, name string, limit int) []string {
	type scored struct {
		name         string
		prefixMatch  bool
		containsTerm bool
		score        int
	}

	query := strings.ToLower(name)
	scoredProjects := make([]scored, 0, len(projects))
	for _, p := range projects {
		candidate := strings.ToLower(p.Name)
		scoredProjects = append(scoredProjects, scored{
			name:         p.Name,
			prefixMatch:  strings.HasPrefix(candidate, query),
			containsTerm: strings.Contains(candidate, query),
			score:        levenshtein(query, candidate),
		})
	}

	sort.Slice(scoredProjects, func(i, j int) bool {
		if scoredProjects[i].prefixMatch != scoredProjects[j].prefixMatch {
			return scoredProjects[i].prefixMatch
		}
		if scoredProjects[i].containsTerm != scoredProjects[j].containsTerm {
			return scoredProjects[i].containsTerm
		}
		if scoredProjects[i].score == scoredProjects[j].score {
			return scoredProjects[i].name < scoredProjects[j].name
		}
		return scoredProjects[i].score < scoredProjects[j].score
	})

	if limit > len(scoredProjects) {
		limit = len(scoredProjects)
	}

	result := make([]string, 0, limit)
	for _, item := range scoredProjects[:limit] {
		result = append(result, item.name)
	}
	return result
}

func hydrate(path string) Project {
	name := filepath.Base(path)
	return Project{
		Name:       name,
		Path:       path,
		AgentsPath: filepath.Join(path, "AGENTS.md"),
		ReadmePath: filepath.Join(path, "README.md"),
		SkillsDir:  filepath.Join(path, "skills"),
	}
}

func levenshtein(a, b string) int {
	if a == b {
		return 0
	}
	if a == "" {
		return len(b)
	}
	if b == "" {
		return len(a)
	}

	prev := make([]int, len(b)+1)
	curr := make([]int, len(b)+1)
	for j := range prev {
		prev[j] = j
	}

	for i := 1; i <= len(a); i++ {
		curr[0] = i
		for j := 1; j <= len(b); j++ {
			cost := 0
			if a[i-1] != b[j-1] {
				cost = 1
			}
			curr[j] = minInt(
				curr[j-1]+1,
				prev[j]+1,
				prev[j-1]+cost,
			)
		}
		copy(prev, curr)
	}

	return prev[len(b)]
}

func minInt(values ...int) int {
	best := values[0]
	for _, value := range values[1:] {
		if value < best {
			best = value
		}
	}
	return best
}
