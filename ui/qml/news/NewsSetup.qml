import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var controller
    signal saved()
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
        Text { text: "News Setup"; color: Theme.colors.textPrimary; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
        AppTextField { id: topic; Layout.fillWidth: true; placeholderText: "News topic"; text: root.controller ? (root.controller.project.topic || "") : "" }
        RowLayout {
            Layout.fillWidth: true
            ComboBox { id: angle; Layout.fillWidth: true; model: ["General Update","Explainer","Breaking Update","Technology","Business","Background","Timeline"] }
            ComboBox { id: language; model: ["English","Khmer"] }
            ComboBox { id: platform; model: ["Generic","TikTok","YouTube Shorts","YouTube","Facebook"] }
            SpinBox { id: duration; from: 15; to: 600; value: 60; editable: true }
        }
        RowLayout { Layout.fillWidth: true; Text { text: "Duration (sec)"; color: Theme.colors.textMuted }; Item { Layout.fillWidth: true }; AppButton { text: "Save Setup"; onClicked: { if (root.controller && root.controller.updateSetup(topic.text, angle.currentText.toLowerCase().replace(/ /g,"_"), language.currentIndex===1?"km":"en", platform.currentText.toLowerCase().replace(/ /g,"_"), duration.value*1000, "")) root.saved() } } }
    }
}
