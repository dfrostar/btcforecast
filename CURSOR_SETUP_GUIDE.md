# Cursor Global Rules Setup Guide

## 🎯 **How to Use These Global Rules in Cursor**

### **1. Setting Up Global Rules in Cursor**

#### **Method 1: Direct Copy-Paste**
1. Open Cursor
2. Go to **Settings** (Ctrl/Cmd + ,)
3. Navigate to **AI** section
4. Find **Custom Instructions** or **Global Rules**
5. Copy the entire content from `CURSOR_GLOBAL_RULES.md`
6. Paste it into the global rules field
7. Save the settings

#### **Method 2: File Reference**
1. In Cursor settings, reference the file:
   ```
   Please follow the rules defined in CURSOR_GLOBAL_RULES.md for this project
   ```

### **2. Key Rules That Will Be Enforced**

#### **Automatic CODE_INDEX.md Updates**
- Cursor will automatically remind you to update `CODE_INDEX.md` when adding new files
- Will suggest proper categorization and descriptions
- Will maintain the timestamp and change summary

#### **Documentation Compliance**
- Will ensure new documentation is added to `DOCUMENT_INDEX.md`
- Will maintain cross-references between related documents
- Will update `ROADMAP.md` for major features

#### **Code Organization**
- Will suggest proper file structure and naming conventions
- Will remind you to use `config.py` for settings
- Will ensure proper error handling and logging

### **3. Expected Behaviors**

#### **When Adding New Files**
Cursor will automatically:
- ✅ Suggest adding the file to `CODE_INDEX.md`
- ✅ Provide a template description with key functions
- ✅ Categorize it in the appropriate section
- ✅ Update the "Last updated" timestamp

#### **When Modifying Existing Files**
Cursor will:
- ✅ Remind you to update the existing entry in `CODE_INDEX.md`
- ✅ Suggest appropriate change summaries
- ✅ Maintain consistency with existing documentation

#### **When Committing Code**
Cursor will:
- ✅ Suggest proper commit message format
- ✅ Remind you to include "Updated CODE_INDEX.md" when applicable
- ✅ Ensure all documentation is current

### **4. Priority Rules Enforcement**

The following rules will be **strictly enforced**:

1. **ALWAYS** update CODE_INDEX.md when adding/modifying files
2. **NEVER** commit code without proper documentation
3. **ALWAYS** use configuration management for settings
4. **ALWAYS** implement proper error handling
5. **ALWAYS** maintain health monitoring
6. **ALWAYS** follow PowerShell standards for Windows
7. **ALWAYS** optimize for SEO where applicable
8. **ALWAYS** use instructor for structured outputs when possible

### **5. Compliance Checklist Integration**

Cursor will automatically check for:
- [ ] CODE_INDEX.md updated with any file changes
- [ ] DOCUMENT_INDEX.md updated if new docs added
- [ ] ROADMAP.md updated if major features completed
- [ ] All new files have proper documentation
- [ ] Configuration changes documented
- [ ] Error handling implemented
- [ ] Logging added where appropriate

### **6. Custom Instructions for This Project**

Add these specific instructions to Cursor:

```
For the BTC Forecasting project:
1. ALWAYS maintain CODE_INDEX.md compliance
2. USE PowerShell for Windows 11 compatibility
3. IMPLEMENT instructor for structured outputs where applicable
4. OPTIMIZE for SEO schema and tags
5. KEEP code organized with detailed comments
6. MAINTAIN application roadmap and document index
7. FOLLOW the rules in CURSOR_GLOBAL_RULES.md
```

### **7. Troubleshooting**

#### **If Rules Aren't Being Followed**
1. Check that global rules are properly saved in Cursor settings
2. Ensure the project is recognized as the BTC Forecasting project
3. Restart Cursor if needed
4. Verify the rules are being applied to new conversations

#### **If Documentation Gets Out of Sync**
1. Run a compliance check using the checklist in `CURSOR_GLOBAL_RULES.md`
2. Update `CODE_INDEX.md` manually if needed
3. Ensure all new files are properly documented
4. Commit changes with proper commit messages

### **8. Benefits of Using These Rules**

#### **For Development**
- ✅ Consistent code organization
- ✅ Automatic documentation maintenance
- ✅ Better code quality and standards
- ✅ Easier onboarding for new contributors

#### **For Maintenance**
- ✅ Clear project structure
- ✅ Up-to-date documentation
- ✅ Proper error handling
- ✅ Health monitoring

#### **For Collaboration**
- ✅ Standardized workflows
- ✅ Clear communication
- ✅ Reduced technical debt
- ✅ Better project visibility

### **9. Integration with Existing Workflow**

These rules complement your existing workflow by:
- **Enhancing** the current documentation system
- **Automating** compliance checks
- **Standardizing** development practices
- **Improving** code quality and maintainability

### **10. Monitoring and Updates**

#### **Regular Reviews**
- Review global rules monthly for relevance
- Update rules based on project evolution
- Ensure rules align with team practices

#### **Rule Evolution**
- Add new rules as the project grows
- Remove outdated rules
- Refine existing rules based on experience

---

## 🚀 **Quick Start**

1. **Copy** the content from `CURSOR_GLOBAL_RULES.md`
2. **Paste** into Cursor's global rules setting
3. **Save** the settings
4. **Start** coding with automatic compliance enforcement

---

**Last Updated**: 2025-06-25  
**Status**: Ready for Implementation  
**Compatibility**: Cursor AI Assistant 