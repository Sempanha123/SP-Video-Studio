import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var controller
    property string projectLanguage: "en"
    signal created()
    implicitHeight: form.implicitHeight + Theme.spacing.xl * 2
    ColumnLayout {
        id: form; anchors.fill: parent; anchors.margins: Theme.spacing.xl; spacing: Theme.spacing.lg
        ColumnLayout { Layout.fillWidth: true; spacing: 3
            Text { text: "Plan your video"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
            Text { Layout.fillWidth: true; text: "Offline planning turns your idea or existing project content into a structured production plan. No project text is sent anywhere."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap }
        }
        GridLayout { Layout.fillWidth: true; columns: width < 760 ? 1 : 2; columnSpacing: Theme.spacing.md; rowSpacing: Theme.spacing.md
            ColumnLayout { Layout.fillWidth: true; Text { text: "Workflow"; color: Theme.colors.textSecondary; font.family: Theme.type.family }; AppComboBox { id: workflow; Layout.fillWidth: true; model: ["News","Story","Translate","Video","Shorts"] } }
            ColumnLayout { Layout.fillWidth: true; Text { text: "Platform"; color: Theme.colors.textSecondary; font.family: Theme.type.family }; AppComboBox { id: platform; Layout.fillWidth: true; model: ["TikTok","YouTube Shorts","Instagram Reels","YouTube","Facebook","Generic"] } }
            ColumnLayout { Layout.fillWidth: true; Text { text: "Content Source"; color: Theme.colors.textSecondary; font.family: Theme.type.family }; AppComboBox { id: sourceType; Layout.fillWidth: true; model: ["Manual Idea","Existing Script","Transcript","Translation","Existing Scenes"]; onCurrentIndexChanged: sourceBox.currentIndex = 0 } }
            ColumnLayout { Layout.fillWidth: true; Text { text: "Language"; color: Theme.colors.textSecondary; font.family: Theme.type.family }; AppComboBox { id: language; Layout.fillWidth: true; model: ["English","Khmer"]; Component.onCompleted: currentIndex = root.projectLanguage === "km" ? 1 : 0 } }
            ColumnLayout { Layout.fillWidth: true; Text { text: "Target Duration"; color: Theme.colors.textSecondary; font.family: Theme.type.family }; AppComboBox { id: duration; Layout.fillWidth: true; model: ["15 sec","30 sec","45 sec","60 sec","90 sec","2 min","3 min","5 min"]; currentIndex: 3 } }
            ColumnLayout { Layout.fillWidth: true; Text { text: "Audience"; color: Theme.colors.textSecondary; font.family: Theme.type.family }; AppComboBox { id: audience; Layout.fillWidth: true; model: ["General","Beginners","Technical","Professional","Young Adult","Business"] } }
            ColumnLayout { Layout.fillWidth: true; Text { text: "Style"; color: Theme.colors.textSecondary; font.family: Theme.type.family }; AppComboBox { id: style; Layout.fillWidth: true; model: ["Modern","Clean","Professional","News","Documentary","Storytelling","Energetic","Minimal","Educational","Creator"] } }
            ColumnLayout { Layout.fillWidth: true; Text { text: "Pace"; color: Theme.colors.textSecondary; font.family: Theme.type.family }; AppComboBox { id: pace; Layout.fillWidth: true; model: ["Balanced","Fast","Slow"] } }
        }
        ColumnLayout {
            Layout.fillWidth: true; visible: sourceType.currentIndex === 0
            Text { text: "Idea"; color: Theme.colors.textSecondary; font.family: Theme.type.family }
            TextArea { id: idea; Layout.fillWidth: true; Layout.preferredHeight: 100; wrapMode: TextEdit.Wrap; placeholderText: "Describe what the video should be about. AI Director will plan structure only; it will not research or invent facts." }
        }
        ColumnLayout {
            Layout.fillWidth: true; visible: sourceType.currentIndex !== 0
            Text { text: "Choose Source"; color: Theme.colors.textSecondary; font.family: Theme.type.family }
            AppComboBox { id: sourceBox; Layout.fillWidth: true; model: {
                    if (!root.controller) return []
                    var key=["idea","script","transcript","translation","scenes"][sourceType.currentIndex]
                    return root.controller.sourceOptions[key] || []
                }; textRole: "name" }
        }
        RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true }; AppButton { text: "Create Plan"; onClicked: {
                    var workflowCodes=["news","story","translate","video","shorts"]
                    var platformCodes=["tiktok","youtube_shorts","instagram_reels","youtube","facebook","generic"]
                    var sourceCodes=["idea","script","transcript","translation","scenes"]
                    var durationValues=[15000,30000,45000,60000,90000,120000,180000,300000]
                    var audienceCodes=["general","beginners","technical","professional","young_adult","business"]
                    var styleCodes=["modern","clean","professional","news","documentary","storytelling","energetic","minimal","educational","creator"]
                    var paceCodes=["balanced","fast","slow"]
                    var sourceId = sourceType.currentIndex===0 ? "" : (sourceBox.currentIndex>=0 && sourceBox.model.length ? sourceBox.model[sourceBox.currentIndex].id : "")
                    if (root.controller.createPlan(workflowCodes[workflow.currentIndex],sourceCodes[sourceType.currentIndex],sourceId,idea.text,platformCodes[platform.currentIndex],language.currentIndex===1?"km":"en",durationValues[duration.currentIndex],audienceCodes[audience.currentIndex],styleCodes[style.currentIndex],paceCodes[pace.currentIndex],"neutral")) root.created()
                } } }
    }
}
