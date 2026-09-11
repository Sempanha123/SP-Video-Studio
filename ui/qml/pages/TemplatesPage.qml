import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import SPVideoStudio.Phase24 1.0
import "../theme"
import "../components"
import "../templates" as TemplateUi

Item {
    id:root
    signal navigateRequested(string page,string workflow)
    signal toastRequested(string message,string variant)
    property string selectedId:""

    function choose(id) { if(!id)return; root.selectedId=id; Templates.selectTemplate(id) }
    Component.onCompleted: { Templates.setCurrentProject(typeof projectController !== "undefined" ? (projectController.currentProject.id || "") : ""); Templates.refresh() }
    Connections { target:Templates; function onOperationSucceeded(message){root.toastRequested(message,"success")} function onOperationFailed(message){root.toastRequested(message,"error")} function onProjectCreated(projectId){ if(typeof projectController !== "undefined" && projectController.openProject(projectId)) root.navigateRequested("workspace","") } }
    Connections { target:typeof projectController !== "undefined" ? projectController : null; ignoreUnknownSignals:true; function onCurrentProjectChanged(){Templates.setCurrentProject(projectController.currentProject.id || "")} }

    ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.md
        RowLayout { Layout.fillWidth:true; spacing:Theme.spacing.md
            ColumnLayout { Layout.fillWidth:true; spacing:2
                Text { text:"Templates"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.titleLarge; font.weight:Theme.type.semibold }
                Text { text:"Reusable structure and style · local, versioned, privacy-safe"; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
            }
            SecondaryButton { text:"Import"; iconName:"import"; onClicked:importDialog.open() }
            SecondaryButton { text:"Save Current"; enabled:Templates.currentProjectId !== ""; onClicked:saveDialog.open() }
        }

        RowLayout { Layout.fillWidth:true; spacing:Theme.spacing.sm
            AppTextField { Layout.preferredWidth:260; placeholderText:"Search templates"; onTextChanged:Templates.setQuery(text) }
            AppComboBox { id:category; Layout.preferredWidth:190; model:Templates.categories; onActivated:Templates.setCategory(currentText) }
            AppComboBox { id:sort; Layout.preferredWidth:170; model:["Recommended","Recently Used","Name"]; onActivated:Templates.setSortMode(["recommended","recent","name"][currentIndex]) }
            Item { Layout.fillWidth:true }
            Text { text:Templates.templates.length + " templates"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
        }

        SplitView { Layout.fillWidth:true; Layout.fillHeight:true; orientation:root.width<1000?Qt.Vertical:Qt.Horizontal
            ScrollView { SplitView.fillWidth:true; SplitView.preferredWidth:root.width*.62; clip:true; contentWidth:availableWidth
                GridLayout { width:parent.width; columns:width<720?1:2; columnSpacing:Theme.spacing.md; rowSpacing:Theme.spacing.md
                    Repeater { model:Templates.templates; delegate:TemplateUi.TemplateCard { required property var modelData; Layout.fillWidth:true; templateData:modelData; onSelected:function(id){root.choose(id)}; onUseRequested:function(id){root.choose(id);applyDialog.applyCurrent=false;applyDialog.open()} } }
                }
            }
            ScrollView { SplitView.preferredWidth:390; SplitView.minimumWidth:330; clip:true; contentWidth:availableWidth
                ColumnLayout { width:parent.width; spacing:Theme.spacing.md
                    TemplateUi.TemplatePreview { Layout.fillWidth:true; Layout.preferredHeight:420; templateData:Templates.selectedTemplate }
                    TemplateUi.TemplateDetails { Layout.fillWidth:true; visible:Templates.selectedTemplate.id !== undefined; templateData:Templates.selectedTemplate
                        onUseRequested:{applyDialog.applyCurrent=false;applyDialog.open()}
                        onDuplicateRequested:Templates.duplicateTemplate(root.selectedId)
                        onDeleteRequested:deleteConfirm.open()
                        onExportRequested:exportDialog.open()
                    }
                    AppButton { Layout.fillWidth:true; visible:Templates.currentProjectId !== "" && Templates.selectedTemplate.id !== undefined; text:"Apply to Current Project"; variant:"secondary"; onClicked:{applyDialog.applyCurrent=true;applyDialog.open()} }
                }
            }
        }
    }

    TemplateUi.TemplateApplyDialog { id:applyDialog; templateData:Templates.selectedTemplate; currentProjectId:Templates.currentProjectId
        onCreateRequested:function(id,title,language,aspect,resolutions,components){Templates.createProject(id,title,language,aspect,resolutions,components)}
        onApplyRequested:function(id,resolutions,components,mode,sceneId){Templates.applyToCurrent(id,resolutions,components,mode,sceneId)}
    }
    TemplateUi.SaveTemplateDialog { id:saveDialog; onSaveRequested:function(name,category,description,components,includeText){Templates.saveCurrentAsTemplate(name,category,description,components,includeText)} }
    TemplateUi.TemplateImportDialog { id:importDialog; onImportRequested:function(path,conflict){Templates.importTemplate(path,conflict)} }

    FileDialog { id:exportDialog; title:"Export Template"; fileMode:FileDialog.SaveFile; nameFilters:["MMO Video Templates (*.mmovtemplate)"]; onAccepted:Templates.exportTemplate(root.selectedId,selectedFile.toString()) }
    AppDialog { id:deleteConfirm; width:430; parent:Overlay.overlay; x:(parent.width-width)/2; y:(parent.height-height)/2; header:null; footer:null
        contentItem:ColumnLayout { spacing:Theme.spacing.md; Text{text:"Delete this user template?";color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.heading;font.weight:Theme.type.semibold}; Text{Layout.fillWidth:true;text:"Projects already created from it will not be affected.";color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodySmall;wrapMode:Text.WordWrap}; RowLayout{Layout.fillWidth:true;Item{Layout.fillWidth:true};SecondaryButton{text:"Cancel";onClicked:deleteConfirm.close()};AppButton{text:"Delete";variant:"danger";onClicked:{Templates.deleteTemplate(root.selectedId);deleteConfirm.close()}}} }
    }
}
