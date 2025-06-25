# Cursor Global Rules for BTC Forecasting Project

## 🎯 **Core Documentation Management Rules**

### **1. CODE_INDEX.md Maintenance**
- **ALWAYS** update `CODE_INDEX.md` when adding, removing, or significantly modifying any file
- **REQUIRED** for every new file: Add entry with brief description and key functions/classes
- **REQUIRED** for file modifications: Update existing entry with change summary
- **FORMAT**: Use consistent structure with file path, description, and key functions
- **CATEGORIZE**: Group files by functional categories (API, Data, Models, etc.)
- **TIMESTAMP**: Update "Last updated" field with current date and change summary

### **2. Documentation Index Compliance**
- **ALWAYS** update `DOCUMENT_INDEX.md` when adding new documentation files
- **REQUIRED** for new docs: Add entry with purpose and target audience
- **MAINTAIN** cross-references between related documentation
- **KEEP** documentation hierarchy organized and navigable

### **3. Roadmap Synchronization**
- **ALWAYS** update `ROADMAP.md` when implementing major features or improvements
- **TRACK** completed milestones and update progress
- **ADD** new planned features and improvements
- **MAINTAIN** realistic timelines and priorities

## 📝 **Code Organization Rules**

### **4. File Structure Standards**
- **ORGANIZE** files by functional purpose (API, Data, Models, etc.)
- **USE** consistent naming conventions (snake_case for Python, kebab-case for docs)
- **MAINTAIN** logical directory structure
- **AVOID** deep nesting (max 3 levels)

### **5. Import and Dependency Management**
- **KEEP** imports organized and minimal
- **USE** relative imports within the project
- **UPDATE** `requirements.txt` and `environment.yml` when adding dependencies
- **DOCUMENT** any special dependency requirements

### **6. Configuration Management**
- **USE** `config.py` for all configuration settings
- **AVOID** hardcoded values in code
- **SUPPORT** environment variable overrides
- **DOCUMENT** all configuration options

## 🔧 **Development Workflow Rules**

### **7. Git Commit Standards**
- **REQUIRED** commit message format: `"Category: Brief description of changes"`
- **INCLUDE** in commit message: "Updated CODE_INDEX.md" when applicable
- **GROUP** related changes in single commits
- **AVOID** committing incomplete features

### **8. Code Quality Standards**
- **ADD** detailed comments for complex logic (indexed to CODE_INDEX.md)
- **USE** type hints for all function parameters and returns
- **FOLLOW** PEP 8 style guidelines
- **INCLUDE** docstrings for all public functions and classes

### **9. Error Handling and Logging**
- **IMPLEMENT** comprehensive error handling
- **USE** structured logging with appropriate levels
- **INCLUDE** error context and recovery suggestions
- **LOG** to appropriate files in `logs/` directory

## 🚀 **Feature Development Rules**

### **10. New Feature Implementation**
- **REQUIRED** before coding: Update ROADMAP.md with feature plan
- **REQUIRED** after implementation: Update CODE_INDEX.md with new files/functions
- **REQUIRED** after completion: Update IMPROVEMENTS.md with feature summary
- **INCLUDE** usage examples in documentation

### **11. API Development Standards**
- **FOLLOW** RESTful design principles
- **INCLUDE** comprehensive error responses
- **ADD** health check endpoints
- **DOCUMENT** all endpoints with examples
- **IMPLEMENT** request/response monitoring

### **12. Model and Data Pipeline Rules**
- **SAVE** models with version information
- **INCLUDE** data validation and preprocessing
- **DOCUMENT** feature engineering steps
- **MAINTAIN** data lineage and provenance
- **IMPLEMENT** model performance monitoring

## 📊 **Monitoring and Maintenance Rules**

### **13. Health Monitoring**
- **USE** `monitoring.py` for all system metrics
- **IMPLEMENT** health checks for all critical components
- **TRACK** API performance and error rates
- **ALERT** on system degradation

### **14. Performance Optimization**
- **MONITOR** resource usage (CPU, Memory, Disk)
- **OPTIMIZE** slow operations and bottlenecks
- **CACHE** frequently accessed data
- **DOCUMENT** performance improvements

### **15. Security and Best Practices**
- **VALIDATE** all user inputs
- **SANITIZE** data before processing
- **USE** environment variables for sensitive data
- **IMPLEMENT** rate limiting where appropriate
- **KEEP** dependencies updated

## 🎨 **User Experience Rules**

### **16. Dashboard and UI Standards**
- **MAINTAIN** consistent UI/UX patterns
- **PROVIDE** clear error messages and help text
- **INCLUDE** loading states and progress indicators
- **ENSURE** responsive design for different screen sizes
- **ADD** keyboard shortcuts for power users

### **17. Documentation Quality**
- **WRITE** clear, concise documentation
- **INCLUDE** practical examples and use cases
- **MAINTAIN** up-to-date screenshots and diagrams
- **PROVIDE** troubleshooting guides
- **USE** consistent terminology throughout

## 🔄 **Automation and Scripts Rules**

### **18. PowerShell Script Standards**
- **USE** `run_app.ps1` for application startup
- **USE** `restart_app.ps1` for process management
- **INCLUDE** error handling and user feedback
- **DOCUMENT** script parameters and usage
- **TEST** scripts on clean environments

### **19. CI/CD and Deployment**
- **MAINTAIN** working Docker configurations
- **TEST** deployment scripts regularly
- **DOCUMENT** deployment procedures
- **INCLUDE** rollback procedures
- **MONITOR** deployment success rates

## 📈 **SEO and Optimization Rules**

### **20. SEO Optimization**
- **INCLUDE** proper meta tags and descriptions
- **USE** semantic HTML structure
- **OPTIMIZE** page load times
- **IMPLEMENT** structured data (JSON-LD)
- **MAINTAIN** clean URL structure

### **21. Search and Discovery**
- **USE** descriptive file and function names
- **INCLUDE** comprehensive README files
- **MAINTAIN** clear project structure
- **ADD** tags and categories for content
- **IMPLEMENT** search functionality where appropriate

## 🛠 **Tool Integration Rules**

### **22. Instructor Integration**
- **USE** https://github.com/567-labs/instructor for structured outputs
- **IMPLEMENT** where applicable for API responses
- **DOCUMENT** structured output schemas
- **MAINTAIN** schema versioning

### **23. Development Environment**
- **USE** PowerShell for Windows 11 compatibility
- **MAINTAIN** consistent development environment
- **DOCUMENT** setup procedures
- **INCLUDE** environment-specific configurations

## 📋 **Compliance Checklist**

### **Before Every Commit:**
- [ ] CODE_INDEX.md updated with any file changes
- [ ] DOCUMENT_INDEX.md updated if new docs added
- [ ] ROADMAP.md updated if major features completed
- [ ] All new files have proper documentation
- [ ] Configuration changes documented
- [ ] Error handling implemented
- [ ] Logging added where appropriate

### **Before Every Release:**
- [ ] All documentation is current and accurate
- [ ] Performance metrics are acceptable
- [ ] Security review completed
- [ ] Dependencies are up to date
- [ ] Deployment scripts tested
- [ ] User guides updated

## 🎯 **Priority Rules (Must Follow)**

1. **ALWAYS** update CODE_INDEX.md when adding/modifying files
2. **NEVER** commit code without proper documentation
3. **ALWAYS** use configuration management for settings
4. **ALWAYS** implement proper error handling
5. **ALWAYS** maintain health monitoring
6. **ALWAYS** follow PowerShell standards for Windows
7. **ALWAYS** optimize for SEO where applicable
8. **ALWAYS** use instructor for structured outputs when possible

---

**Last Updated**: 2025-06-25  
**Version**: 1.0.0  
**Status**: Active - Must be followed for all development work 