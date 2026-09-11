import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    id: root
    property var controller
    property var playbackController
    signal exportRequested()

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacing.md

        TranscriptToolbar {
            Layout.fillWidth: true
            controller: root.controller
            onExportRequested: root.exportRequested()
        }

        ListView {
            id: transcriptList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: Theme.spacing.sm
            model: root.controller ? root.controller.segments : null
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}
            delegate: TranscriptSegmentRow {
                required property string segmentId
                required property int startMs
                required property int endMs
                required property string startText
                required property string endText
                required property string segmentText
                required property string originalText
                required property bool edited
                width: transcriptList.width
                onTextEdited: function(id, value) { if (root.controller) root.controller.editSegment(id, value) }
                onResetRequested: function(id) { if (root.controller) root.controller.resetSegment(id) }
                onPlayRequested: function(id, start) { if (root.controller) root.controller.playSegment(root.controller.mediaId, start, true) }
            }

            footer: Item { width: 1; height: Theme.spacing.lg }
        }
    }
}
