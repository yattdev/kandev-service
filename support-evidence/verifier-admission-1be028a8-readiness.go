// Host Support-only adapter for request 1be028a8. No task-facing capability.
package main

import (
	"crypto/rand"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"github.com/gorilla/websocket"
	"github.com/mattn/go-sqlite3"
)

const task = "afdb2ef3-06ca-4cd5-a074-c4e691679da9"
const workspace = "2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd"
const step = "0541923c-2d38-478e-8573-3c5e27e37a31"
const profile = "c06ad00e-0da1-429a-8174-54f97164a289"
const model = "gpt-6.1-sol"
const mainSession = "fafba895-b769-40d5-a840-f6b90b98fcb4"

type Target struct{ Session, Incarnation, OldExecution, Message, Turn, Hash string }

var targets = []Target{
	{"ce9a2b21-226c-41b1-be4c-828c7ef1dfef", "de782256-6dc8-4624-9fff-aec6755fc682", "a44318b3-a799-4ca4-84b0-7a231e6ba531", "24ea3a33-b106-5b56-bb88-9ced18e9e558", "04436262-9a3d-4ef3-ad65-2c21801f7a99", "518f06f78239763f3975cf280231ce02bef17b6e85447231a5e87c9b93e4160d"},
	{"9610084b-03e4-442c-ba8a-3109e06a4123", "702f5f83-ea4a-4e37-9e26-7051524ebc22", "37bdbcdb-ef37-464e-91df-db30186835c6", "22d8f471-e8a5-58ca-b51a-0f3539dab9bd", "be347b62-9f02-401e-be9c-bace319759be", "9b31eb1c96a3f72676b9ccdd2c594ca318c3e9c5a362a492852e3a18edf5f0d2"},
}

type Snapshot struct {
	State, Profile, ConfiguredModel, ActualModel, Incarnation, Execution, ExecutionState, ExecutionProfile, ResumeHash, MessageHash, TurnCompleted string
	TokenPresent, Queued, OpenWorkTurns, PendingInput, WorkTurns, UserMessages                                                                     int
}
type Result struct {
	Session          string `json:"session_id"`
	Status           string `json:"status"`
	Execution        string `json:"execution_id,omitempty"`
	Code             string `json:"code,omitempty"`
	ProtocolReady    bool   `json:"protocol_ready"`
	NoNewWorkTurn    bool   `json:"no_new_work_turn"`
	ModelUnchanged   bool   `json:"model_unchanged"`
	HistoryPreserved bool   `json:"history_preserved"`
}
type Receipt struct {
	Request      string   `json:"request_id"`
	Results      []Result `json:"results"`
	Code         string   `json:"code,omitempty"`
	LeaseRevoked bool     `json:"operator_lease_revoked"`
	TokenExposed bool     `json:"token_exposed"`
}

func fail(s string) error { return errors.New(s) }
func sha(s string) string { v := sha256.Sum256([]byte(s)); return hex.EncodeToString(v[:]) }
func randomHex(n int) (string, error) {
	b := make([]byte, n)
	if _, err := rand.Read(b); err != nil {
		return "", fail("RANDOM_UNAVAILABLE")
	}
	return hex.EncodeToString(b), nil
}
func dbPath() (string, error) {
	b, err := exec.Command("/usr/bin/docker", "inspect", "kandev", "--format", "{{json .Mounts}}").Output()
	if err != nil {
		return "", fail("DEPLOYMENT_MAPPING_UNAVAILABLE")
	}
	var mounts []struct{ Source, Destination string }
	if json.Unmarshal(b, &mounts) != nil {
		return "", fail("DEPLOYMENT_MAPPING_INVALID")
	}
	for _, m := range mounts {
		if m.Destination == "/data" {
			p := filepath.Join(m.Source, "data/kandev.db")
			st, e := os.Stat(p)
			if e == nil && st.Mode().IsRegular() {
				return p, nil
			}
		}
	}
	return "", fail("DATABASE_MAPPING_UNAVAILABLE")
}
func openDB(readOnly bool) (*sql.DB, error) {
	p, err := dbPath()
	if err != nil {
		return nil, err
	}
	sql.Register("support-1be028a8", &sqlite3.SQLiteDriver{ConnectHook: func(c *sqlite3.SQLiteConn) error { return c.RegisterFunc("support_sha256", sha, true) }})
	mode := "rw"
	if readOnly {
		mode = "ro"
	}
	db, err := sql.Open("support-1be028a8", "file:"+p+"?mode="+mode+"&_busy_timeout=10000&_foreign_keys=on")
	if err != nil {
		return nil, fail("DATABASE_UNAVAILABLE")
	}
	db.SetMaxOpenConns(1)
	return db, nil
}
func taskGuard(db *sql.DB) error {
	var w, s, st string
	var archived int
	if db.QueryRow(`SELECT workspace_id,workflow_step_id,state,CASE WHEN archived_at IS NULL THEN 0 ELSE 1 END FROM tasks WHERE id=?`, task).Scan(&w, &s, &st, &archived) != nil {
		return fail("TASK_BINDING_UNAVAILABLE")
	}
	if w != workspace || s != step || st != "REVIEW" || archived != 0 {
		return fail("TASK_BINDING_CHANGED")
	}
	var primaries, matching int
	if db.QueryRow(`SELECT count(*),coalesce(sum(CASE WHEN id=? AND state NOT IN ('FAILED','CANCELLED','COMPLETED') THEN 1 ELSE 0 END),0) FROM task_sessions WHERE task_id=? AND is_primary=1`, mainSession, task).Scan(&primaries, &matching) != nil || primaries != 1 || matching != 1 {
		return fail("MAIN_OWNERSHIP_CHANGED")
	}
	var pm string
	var af int
	if db.QueryRow(`SELECT model,auto_fallback FROM agent_profiles WHERE id=? AND enabled=1`, profile).Scan(&pm, &af) != nil || pm != model || af != 0 {
		return fail("PROFILE_BINDING_CHANGED")
	}
	return nil
}
func snapshot(db *sql.DB, t Target) (Snapshot, error) {
	var s Snapshot
	err := db.QueryRow(`SELECT state,agent_profile_id,queue_incarnation_id,coalesce(json_extract(metadata,'$.runtime_config.model'),''),coalesce(json_extract(metadata,'$.acp_model_state.current_model_id'),'') FROM task_sessions WHERE id=? AND task_id=? AND is_primary=0`, t.Session, task).Scan(&s.State, &s.Profile, &s.Incarnation, &s.ConfiguredModel, &s.ActualModel)
	if err != nil {
		return s, fail("SESSION_BINDING_UNAVAILABLE")
	}
	err = db.QueryRow(`SELECT agent_execution_id,status,execution_profile_id,CASE WHEN length(coalesce(resume_token,''))>0 THEN 1 ELSE 0 END,support_sha256(coalesce(resume_token,'')) FROM executors_running WHERE session_id=?`, t.Session).Scan(&s.Execution, &s.ExecutionState, &s.ExecutionProfile, &s.TokenPresent, &s.ResumeHash)
	if err != nil {
		return s, fail("EXECUTION_BINDING_UNAVAILABLE")
	}
	if db.QueryRow(`SELECT support_sha256(content) FROM task_session_messages WHERE id=? AND task_id=? AND task_session_id=? AND turn_id=?`, t.Message, task, t.Session, t.Turn).Scan(&s.MessageHash) != nil {
		return s, fail("ORIGINAL_MESSAGE_UNAVAILABLE")
	}
	if db.QueryRow(`SELECT coalesce(cast(completed_at AS TEXT),'') FROM task_session_turns WHERE id=? AND task_id=? AND task_session_id=?`, t.Turn, task, t.Session).Scan(&s.TurnCompleted) != nil {
		return s, fail("ORIGINAL_TURN_UNAVAILABLE")
	}
	queries := []struct {
		q string
		v *int
	}{
		{`SELECT count(*) FROM queued_messages WHERE task_id=? AND session_id=?`, &s.Queued},
		{`SELECT count(*) FROM task_session_turns WHERE task_id=? AND task_session_id=? AND completed_at IS NULL AND coalesce(json_extract(metadata,'$.lifecycle_only'),0)=0`, &s.OpenWorkTurns},
		{`SELECT count(*) FROM task_session_messages WHERE task_id=? AND task_session_id=? AND author_type='agent' AND type IN ('clarification_request','permission_request') AND coalesce(json_extract(metadata,'$.status'),'pending') IN ('pending','unknown')`, &s.PendingInput},
		{`SELECT count(*) FROM task_session_turns WHERE task_id=? AND task_session_id=? AND coalesce(json_extract(metadata,'$.lifecycle_only'),0)=0`, &s.WorkTurns},
		{`SELECT count(*) FROM task_session_messages WHERE task_id=? AND task_session_id=? AND author_type='user'`, &s.UserMessages},
	}
	for _, q := range queries {
		if db.QueryRow(q.q, task, t.Session).Scan(q.v) != nil {
			return s, fail("ADMISSION_GUARDS_UNAVAILABLE")
		}
	}
	return s, nil
}
func stable(t Target, s Snapshot) error {
	if s.Profile != profile || s.ConfiguredModel != model || s.Incarnation != t.Incarnation || s.ExecutionProfile != profile {
		return fail("OWNER_OR_CONFIGURATION_CHANGED")
	}
	if s.MessageHash != t.Hash || s.TurnCompleted == "" {
		return fail("ORIGINAL_EVIDENCE_CHANGED")
	}
	if s.Queued != 0 || s.OpenWorkTurns != 0 || s.PendingInput != 0 {
		return fail("FIFO_OR_HUMAN_INPUT_OWNED")
	}
	return nil
}
func before(t Target, s Snapshot) error {
	if err := stable(t, s); err != nil {
		return err
	}
	if s.State != "FAILED" || s.ExecutionState != "failed" || s.Execution != t.OldExecution {
		return fail("ORIGINAL_EXECUTION_NO_LONGER_FAILED")
	}
	if s.TokenPresent != 1 || s.ActualModel != model {
		return fail("SAVED_IDENTITY_OR_MODEL_UNCONFIRMED")
	}
	return nil
}
func after(t Target, b, a Snapshot) error {
	if err := stable(t, a); err != nil {
		return err
	}
	if a.State != "WAITING_FOR_INPUT" || a.ExecutionState != "ready" || a.Execution == "" || a.Execution == t.OldExecution {
		return fail("PROTOCOL_READINESS_NOT_CONFIRMED")
	}
	if a.ActualModel != model {
		return fail("EFFECTIVE_MODEL_NOT_CONFIRMED")
	}
	if a.ResumeHash != b.ResumeHash || a.TurnCompleted != b.TurnCompleted || a.WorkTurns != b.WorkTurns || a.UserMessages != b.UserMessages {
		return fail("CONVERSATION_OR_WORK_HISTORY_CHANGED")
	}
	return nil
}
func lease(db *sql.DB) (string, func() bool, error) {
	var uid string
	if db.QueryRow(`SELECT id FROM users WHERE role='admin' AND status='active' ORDER BY created_at,id LIMIT 1`).Scan(&uid) != nil {
		return "", nil, fail("OPERATOR_AUTHORITY_UNAVAILABLE")
	}
	id, e := randomHex(16)
	if e != nil {
		return "", nil, e
	}
	prefix, e := randomHex(4)
	if e != nil {
		return "", nil, e
	}
	secret, e := randomHex(32)
	if e != nil {
		return "", nil, e
	}
	token := "kandev_pat_" + prefix + "_" + secret
	now := time.Now().UTC()
	_, e = db.Exec(`INSERT INTO auth_api_tokens(id,user_id,name,prefix,token_sha256,created_at,expires_at) VALUES(?,?,?,?,?,?,?)`, id, uid, "support-verifier-readiness-1be028a8", prefix, sha(token), now.Format(time.RFC3339Nano), now.Add(5*time.Minute).Format(time.RFC3339Nano))
	if e != nil {
		return "", nil, fail("OPERATOR_LEASE_UNAVAILABLE")
	}
	revoke := func() bool {
		_, e := db.Exec(`DELETE FROM auth_api_tokens WHERE id=? AND name=?`, id, "support-verifier-readiness-1be028a8")
		return e == nil
	}
	return token, revoke, nil
}
func recoverSession(token string, t Target) (string, error) {
	h := http.Header{}
	h.Set("Authorization", "Bearer "+token)
	dialer := websocket.Dialer{HandshakeTimeout: 5 * time.Second}
	c, resp, e := dialer.Dial("ws://127.0.0.1:38429/ws", h)
	if e != nil {
		if resp != nil && resp.Body != nil {
			resp.Body.Close()
		}
		return "", fail("AUTHENTICATED_CONTROL_UNAVAILABLE")
	}
	defer c.Close()
	c.SetReadLimit(2 << 20)
	c.SetReadDeadline(time.Now().Add(180 * time.Second))
	c.SetWriteDeadline(time.Now().Add(10 * time.Second))
	id := "support-1be028a8-" + t.Session
	if c.WriteJSON(map[string]any{"id": id, "type": "request", "action": "session.recover", "payload": map[string]string{"task_id": task, "session_id": t.Session, "action": "resume"}}) != nil {
		return "", fail("CONTROL_DELIVERY_UNKNOWN")
	}
	for {
		var r struct {
			ID, Type, Action string
			Payload          json.RawMessage
		}
		if c.ReadJSON(&r) != nil {
			return "", fail("CONTROL_RESULT_UNKNOWN_NO_RETRY")
		}
		if r.ID != id {
			continue
		}
		if r.Type != "response" || r.Action != "session.recover" {
			return "", fail("APPLICATION_RECOVERY_REFUSED")
		}
		var p struct {
			Success     bool   `json:"success"`
			Task        string `json:"task_id"`
			Session     string `json:"session_id"`
			Execution   string `json:"agent_execution_id"`
			Disposition string `json:"activation_disposition"`
		}
		if json.Unmarshal(r.Payload, &p) != nil || !p.Success || p.Task != task || p.Session != t.Session || p.Execution == "" || p.Disposition != "" {
			return "", fail("APPLICATION_READINESS_NOT_CONFIRMED")
		}
		return p.Execution, nil
	}
}
func run(apply bool) (out Receipt) {
	out.Request = "1be028a8-6818-4ef8-bbf0-2111b868c73f"
	out.LeaseRevoked = true
	db, e := openDB(!apply)
	if e != nil {
		out.Code = e.Error()
		return
	}
	defer db.Close()
	if e = taskGuard(db); e != nil {
		out.Code = e.Error()
		return
	}
	initial := make([]Snapshot, len(targets))
	for i, t := range targets {
		initial[i], e = snapshot(db, t)
		if e != nil {
			out.Code = e.Error()
			return
		}
		if e = before(t, initial[i]); e != nil {
			out.Code = e.Error()
			return
		}
	}
	if !apply {
		for _, t := range targets {
			out.Results = append(out.Results, Result{Session: t.Session, Status: "PREFLIGHT_ONLY_NO_CAPABILITY_ISSUED"})
		}
		return
	}
	token, revoke, e := lease(db)
	if e != nil {
		out.Code = e.Error()
		return
	}
	defer func() {
		out.LeaseRevoked = revoke()
		if !out.LeaseRevoked {
			out.Code = "OPERATOR_LEASE_REVOCATION_FAILED"
		}
	}()
	for i, t := range targets {
		result := Result{Session: t.Session, Status: "BLOCKED"}
		if e = taskGuard(db); e == nil {
			var s Snapshot
			s, e = snapshot(db, t)
			if e == nil {
				e = before(t, s)
			}
		}
		if e != nil {
			result.Code = e.Error()
			out.Results = append(out.Results, result)
			return
		}
		execution, er := recoverSession(token, t)
		if er != nil {
			result.Code = er.Error()
			out.Results = append(out.Results, result)
			return
		}
		a, er := snapshot(db, t)
		if er == nil {
			er = taskGuard(db)
		}
		if er == nil {
			er = after(t, initial[i], a)
		}
		if er != nil {
			result.Code = er.Error()
			out.Results = append(out.Results, result)
			return
		}
		if a.Execution != execution {
			result.Code = "RESPONSE_EXECUTION_CHANGED"
			out.Results = append(out.Results, result)
			return
		}
		result.Status = "PROTOCOL_READY_NO_WORK_PROMPT"
		result.Execution = execution
		result.ProtocolReady = true
		result.NoNewWorkTurn = true
		result.ModelUnchanged = true
		result.HistoryPreserved = true
		out.Results = append(out.Results, result)
	}
	return
}
func selfTest() bool {
	t := targets[0]
	b := Snapshot{State: "FAILED", Profile: profile, ConfiguredModel: model, ActualModel: model, Incarnation: t.Incarnation, Execution: t.OldExecution, ExecutionState: "failed", ExecutionProfile: profile, TokenPresent: 1, ResumeHash: "synthetic-only", MessageHash: t.Hash, TurnCompleted: "synthetic-completed", WorkTurns: 2, UserMessages: 2}
	if before(t, b) != nil {
		return false
	}
	mutations := []func(*Snapshot){func(s *Snapshot) { s.Profile = "foreign" }, func(s *Snapshot) { s.Incarnation = "replaced" }, func(s *Snapshot) { s.PendingInput = 1 }, func(s *Snapshot) { s.Queued = 1 }, func(s *Snapshot) { s.OpenWorkTurns = 1 }, func(s *Snapshot) { s.TokenPresent = 0 }, func(s *Snapshot) { s.MessageHash = "changed" }, func(s *Snapshot) { s.Execution = "competing" }, func(s *Snapshot) { s.ActualModel = "different" }}
	for _, mutate := range mutations {
		s := b
		mutate(&s)
		if before(t, s) == nil {
			return false
		}
	}
	a := b
	a.State = "WAITING_FOR_INPUT"
	a.ExecutionState = "ready"
	a.Execution = "synthetic-new"
	if after(t, b, a) != nil {
		return false
	}
	for _, mutate := range []func(*Snapshot){func(s *Snapshot) { s.ResumeHash = "replacement" }, func(s *Snapshot) { s.WorkTurns++ }, func(s *Snapshot) { s.UserMessages++ }, func(s *Snapshot) { s.ActualModel = "different" }, func(s *Snapshot) { s.State = "RUNNING" }} {
		s := a
		mutate(&s)
		if after(t, b, s) == nil {
			return false
		}
	}
	return true
}
func main() {
	if len(os.Args) == 2 && os.Args[1] == "--self-test" {
		if !selfTest() {
			fmt.Println(`{"self_test":"FAIL"}`)
			os.Exit(1)
		}
		fmt.Println(`{"self_test":"PASS","negative_guard_cases":14}`)
		return
	}
	if len(os.Args) > 2 || (len(os.Args) == 2 && os.Args[1] != "--apply") {
		fmt.Println(`{"code":"UNSUPPORTED_OPERATION"}`)
		os.Exit(1)
	}
	r := run(len(os.Args) == 2)
	json.NewEncoder(os.Stdout).Encode(r)
	if r.Code != "" {
		os.Exit(1)
	}
	for _, v := range r.Results {
		if v.Code != "" {
			os.Exit(1)
		}
	}
}
