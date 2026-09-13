import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Onboarding 1.0
import "../theme"
import "../components"

SetupStep {
    id: root
    signal createRequested(string title, string workflow, string language, string aspectRatio, int fps)
    signal templateRequested()
    property string workflow: "video"
    property string aspect: workflow === "shorts" ? "9:16" : "16:9"
    title: "Create your first project"
    description: "Pick a simple starting point. You can skip this and go to Home instead."
    GridLayout {
        Layout.fillWidth: true; columns: width < 720 ? 2 : 3; columnSpacing: Theme.spacing.sm; rowSpacing: Theme.spacing.sm
        Repeater {
            model: [
                ["video","Blank Video","Import media and edit manually."],
                ["news","News","Create source-grounded news with reporter, B-roll and captions."],
                ["story","Story","Plan a story, add narration, scenes and music."],
                ["translate","Translate & Dub","Transcribe, translate and dub an existing video."],
                ["shorts","Shorts","Turn existing content into vertical short-form videos."]
            ]
            delegate: RadioCard { required property var modelData; Layout.fillWidth: true; implicitHeight: 82; title: modelData[1]; description: modelData[2]; value: modelData[0]; selected: root.workflow === value; onChosen: { root.workflow=value; root.aspect=value === "shorts" ? "9:16" : "16:9" } }
        }
        AppCard { Layout.fillWidth: true; implicitHeight: 82
            ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.sm
                Text { text: "Start from Template"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodyStrong; font.weight: Theme.type.semibold }
                Text { Layout.fillWidth: true; text: "Templates create the basic scene, tracks and styles for you."; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                SecondaryButton { text: "Browse Templates"; compact: true; onClicked: root.templateRequested() }
            }
        }
    }
    RowLayout { Layout.fillWidth: true
        AppTextField { id: nameField; Layout.fillWidth: true; placeholderText: "Project name"; accessibleName: "Project Name" }
        AppComboBox { id: languageBox; Layout.preferredWidth: 160; model: [Onboarding.defaultContentLanguage]; accessibleName: "Project language" }
        AppComboBox { id: aspectBox; Layout.preferredWidth: 120; model: root.workflow === "news" ? ["16:9","9:16"] : (root.workflow === "shorts" ? ["9:16","1:1"] : ["16:9","9:16","1:1"]); onCurrentTextChanged: root.aspect=currentText; accessibleName: "Aspect ratio" }
        AppButton { text: "Create Project"; enabled: nameField.text.trim().length>0; onClicked: root.createRequested(nameField.text.trim(),root.workflow,Onboarding.defaultContentLanguage,root.aspect,30) }
    }
    InfoBanner { visible: root.workflow === "news"; Layout.fillWidth: true; text: "News reminder: add sources before creating factual news content." }
}
