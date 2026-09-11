import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppDialog {
    id: root
    property var templateData: ({})
    property bool applyCurrent: false
    property string currentProjectId: ""
    property var resolutions: ({})
    signal createRequested(string templateId,string title,string language,string aspect,var resolutions,var components)
    signal applyRequested(string templateId,var resolutions,var components,string mode,string selectedSceneId)
    width: 620; parent: Overlay.overlay; x: (parent.width-width)/2; y: (parent.height-height)/2; header: null; footer: null
    onOpened: { titleField.text=(templateData.name || "Template") + " Project"; language.currentCode="en"; aspect.currentIndex=0; resolutions=({}) }
    function selectedComponents() { var values=[]; for(var i=0;i<(templateData.components||[]).length;i++) values.push(templateData.components[i].type); return values }

    contentItem: ScrollView { implicitHeight: Math.min(650, parent ? parent.height*0.8 : 650); contentWidth: availableWidth
        ColumnLayout { width: parent.width; spacing: Theme.spacing.md
            Text { text: root.applyCurrent ? "Apply Template" : "Create from Template"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            InfoBanner { Layout.fillWidth: true; variant: "info"; text: root.applyCurrent ? "Existing content is preserved in Merge mode. Required unresolved placeholders remain marked for setup." : "Templates copy reusable structure into the new project. They never create a live dependency on the installed template." }
            AppTextField { id:titleField; Layout.fillWidth:true; visible:!root.applyCurrent; placeholderText:"Project name" }
            LanguagePicker { id:language; Layout.fillWidth:true; visible:!root.applyCurrent; currentCode:"en"; onCodeSelected:function(code){root.resolutions.project_language=code} }
            ColumnLayout { Layout.fillWidth:true; visible:!root.applyCurrent
                Text { text:"Aspect ratio"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
                AppComboBox { id:aspect; Layout.fillWidth:true; model: (root.templateData.aspects && root.templateData.aspects.length) ? root.templateData.aspects : ["16:9","9:16","1:1"] }
            }
            Text { text:"Placeholder setup"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall; font.weight:Theme.type.semibold }
            Text { Layout.fillWidth:true; text:"You can resolve IDs now, or leave them blank and finish setup inside the project. Built-in templates never silently pick media or private voices."; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption; wrapMode:Text.WordWrap }
            Repeater { model: root.templateData.placeholders || root.templateData.requiredPlaceholders || []; delegate: ColumnLayout { required property var modelData; Layout.fillWidth:true
                Text { text:(modelData.label || modelData.id) + (modelData.required ? " *" : ""); color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
                AppTextField { Layout.fillWidth:true; placeholderText: modelData.type === "voice" ? "Voice ID (optional)" : modelData.type === "language" ? "Language code" : "Project media/value ID or asset:path"; onTextChanged:{root.resolutions[modelData.id]=text} }
            } }
            RowLayout { Layout.fillWidth:true
                Item { Layout.fillWidth:true }
                SecondaryButton { text:"Cancel"; onClicked:root.close() }
                AppButton { text:root.applyCurrent ? "Apply Merge" : "Create Project"; onClicked:{
                    var comps=root.selectedComponents();
                    if(root.applyCurrent) root.applyRequested(root.templateData.id||"",root.resolutions,comps,"merge","")
                    else root.createRequested(root.templateData.id||"",titleField.text,language.currentCode,aspect.currentText,root.resolutions,comps)
                    root.close()
                } }
            }
        }
    }
}
