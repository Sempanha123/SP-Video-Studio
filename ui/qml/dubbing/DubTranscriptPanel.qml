import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id: root
    required property var controller
    signal navigateRequested(string mode)
    implicitHeight: 140
    ColumnLayout { anchors.fill:parent; anchors.margins:Theme.spacing.lg; spacing:Theme.spacing.sm
        Text { text:"2 · Transcript"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }
        RowLayout { Layout.fillWidth:true
            AppComboBox { id:transcript; Layout.fillWidth:true; model:controller.transcriptOptions; textRole:"label" }
            AppButton { text:"Link Transcript"; enabled:transcript.currentIndex>=0; onClicked:controller.linkTranscript(transcript.model[transcript.currentIndex].id) }
            SecondaryButton { text:"Review"; onClicked:root.navigateRequested("transcription") }
        }
        Text { text:controller.project.transcriptId ? "Transcript linked. Review warnings before translation when practical." : "Uses the existing faster-whisper transcription workflow."; color:Theme.colors.textSecondary }
    }
}
