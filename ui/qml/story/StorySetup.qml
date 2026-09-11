import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id: root
    property var controller
    implicitHeight: 320
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
        SectionHeader { title: "Story Idea"; subtitle: "Plan the narrative first. Production uses the shared Script, Voice, Scenes, Subtitles, Timeline and Export tools." }
        RowLayout { Layout.fillWidth: true; spacing: Theme.spacing.md
            AppTextField { id: titleField; Layout.fillWidth: true; placeholderText: "Story title"; text: root.controller ? (root.controller.story.title || "") : "" }
            AppComboBox { id: typeBox; Layout.preferredWidth: 210; model: ["Short Story","Documentary Story","Educational Story","Motivational Story","Mystery","Drama","Adventure","Biography Style","Explainer Story","Custom"] }
        }
        TextArea { id: ideaField; Layout.fillWidth: true; Layout.fillHeight: true; placeholderText: "Describe the story idea or prompt…"; wrapMode: TextEdit.Wrap; text: root.controller ? (root.controller.story.idea || "") : ""; color: Theme.colors.textPrimary; font.family: Theme.type.family; background: Rectangle { radius: Theme.radius.medium; color: Theme.colors.surface2; border.color: Theme.colors.border } }
        RowLayout { Layout.fillWidth: true; spacing: Theme.spacing.sm
            AppComboBox { id: languageBox; model: ["English","Khmer"] }
            AppComboBox { id: toneBox; model: ["Warm","Calm","Dramatic","Inspirational","Serious","Friendly","Suspenseful","Educational","Neutral"] }
            AppComboBox { id: audienceBox; model: ["General","Young Audience","Adult","Professional","Educational"] }
            AppComboBox { id: paceBox; model: ["Balanced","Slow","Fast"] }
            AppComboBox { id: durationBox; model: ["30 sec","60 sec","90 sec","2 min","3 min","5 min","10 min"] }
            Item { Layout.fillWidth: true }
            AppButton { text: "Save Story"; onClicked: if (root.controller) root.controller.updateSetup(titleField.text, ideaField.text, typeBox.currentText.toLowerCase().replace(/ /g,"_"), languageBox.currentIndex===1?"km":"en", toneBox.currentText.toLowerCase(), [30000,60000,90000,120000,180000,300000,600000][durationBox.currentIndex], audienceBox.currentText.toLowerCase().replace(/ /g,"_"), paceBox.currentText.toLowerCase()) }
        }
    }
}
