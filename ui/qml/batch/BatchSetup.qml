import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Item {
    id: root
    property var controller
    property string batchName: "New Batch"
    property string templateId: ""
    property string outputFolder: ""
    signal nextRequested()
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.md
        Text { text: "1. Template"; color: Theme.colors.textPrimary; font.pixelSize: Theme.type.titleMedium; font.weight: Theme.type.semibold }
        AppTextField { Layout.fillWidth: true; accessibleName: "Batch name"; placeholderText: "Batch name"; text: root.batchName; onTextChanged: root.batchName=text }
        AppComboBox {
            id: templates
            accessibleName: "Batch template"
            Layout.fillWidth: true
            model: root.controller ? root.controller.templateChoices : []
            textRole: "name"; valueRole: "id"
            onActivated: root.templateId = currentValue || ""
            Component.onCompleted: if (count>0 && !root.templateId) root.templateId=currentValue || ""
        }
        Text { text: templates.currentIndex>=0 && templates.model.length ? ((templates.model[templates.currentIndex].category||"")+" · v"+(templates.model[templates.currentIndex].version||"1.0")) : "Choose a Phase 24 template"; color: Theme.colors.textSecondary }
        AppTextField { Layout.fillWidth: true; accessibleName: "Batch output folder"; placeholderText: "Output folder"; text: root.outputFolder; onTextChanged: root.outputFolder=text }
        Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; text: "Batch Factory captures the selected Phase 24 template version when the Batch is created. Running work will not change if the installed template is edited later." }
        AppButton { text: "Continue to Data"; enabled: root.templateId.length>0 && root.outputFolder.length>0; onClicked: root.nextRequested() }
        Item { Layout.fillHeight: true }
    }
}
