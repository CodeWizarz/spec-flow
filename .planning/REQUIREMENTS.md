## v1 Requirements

### Signals
- [ ] **SIG-01**: User can upload/input customer feedback (text, files)
- [ ] **SIG-02**: System stores signals with metadata (source, date, user)
- [ ] **SIG-03**: User can view a minimal list/detail of stored signals

### Insights
- [ ] **INS-01**: System analyzes signals to extract recurring themes
- [ ] **INS-02**: System identifies core problems from extracted themes
- [ ] **INS-03**: User can view summary of insights mapped to exact customer feedback (quotes)

### Specs
- [ ] **SPC-01**: System generates full implementation spec addressing insights
- [ ] **SPC-02**: Spec includes feature recommendation, UI changes, data model changes, workflow changes
- [ ] **SPC-03**: Spec outputs development tasks formatted for AI coding agents
- [ ] **SPC-04**: User can review and export the generated spec

## v2 Requirements
- Automated integrations with Slack/Zendesk for signals
- Spec execution/deployment tracking

## Out of Scope
- Rebuilding Plane features — we are extending Plane
- Complex reporting dashboards — keep UI minimal
- Automated code execution — we only output tasks securely
