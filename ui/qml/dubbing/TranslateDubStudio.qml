import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    id: root
    required property var controller
    signal navigateRequested(string mode)
    property string tab: "overview"

    Connections {
        target: controller
        function onNavigationRequested(mode) { root.navigateRequested(mode) }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacing.md
        RowLayout {
            Layout.fillWidth: true
            Text { text: "Translate & Dub"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
            Item { Layout.fillWidth: true }
            Text { text: controller.readiness.state || "Not Ready"; color: Theme.colors.textSecondary; font.family: Theme.type.family }
        }
        ScrollView {
            Layout.fillWidth: true; Layout.fillHeight: true
            contentWidth: availableWidth
            ColumnLayout {
                width: parent.width; spacing: Theme.spacing.md
                DubSetup { Layout.fillWidth: true; controller: root.controller; onNavigateRequested: root.navigateRequested(mode) }
                DubTranscriptPanel { Layout.fillWidth: true; controller: root.controller; onNavigateRequested: root.navigateRequested(mode) }
                DubTranslationPanel { Layout.fillWidth: true; controller: root.controller; onNavigateRequested: root.navigateRequested(mode) }
                DubVoicePanel { Layout.fillWidth: true; controller: root.controller; onNavigateRequested: root.navigateRequested(mode) }
                DubSegmentList { Layout.fillWidth: true; controller: root.controller }
                DubAudioMixPanel { Layout.fillWidth: true; controller: root.controller }
                DubPreview { Layout.fillWidth: true; controller: root.controller }
                DubReadiness { Layout.fillWidth: true; controller: root.controller; onNavigateRequested: root.navigateRequested(mode) }
            }
        }
    }
}
