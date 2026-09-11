import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id: root
    required property var controller
    signal navigateRequested(string mode)
    implicitHeight: 210
    ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
        Text { text: "1 · Source video"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
        RowLayout { Layout.fillWidth: true
            AppComboBox { id:video; Layout.fillWidth:true; model:controller.sourceVideos; textRole:"name" }
            AppComboBox { id:source; Layout.preferredWidth:150; model:[{"id":"auto","name":"Auto Detect"},{"id":"en","name":"English"},{"id":"km","name":"Khmer"}]; textRole:"name" }
            Text { text:"→"; color:Theme.colors.textMuted }
            AppComboBox { id:target; Layout.preferredWidth:140; model:[{"id":"km","name":"Khmer"},{"id":"en","name":"English"}]; textRole:"name" }
            AppButton { text:"Use Video"; enabled:video.currentIndex>=0; onClicked:{ var s=source.model[source.currentIndex].id; var t=target.model[target.currentIndex].id; if(s===t){ return } controller.updateSetup(video.model[video.currentIndex].id,s,t) } }
        }
        Text { Layout.fillWidth:true; text:controller.project.sourceMediaId ? "Source selected. Original video timing remains canonical." : "Choose an imported project video. Source and target languages must differ."; color:Theme.colors.textSecondary; wrapMode:Text.Wrap }
        RowLayout { Layout.fillWidth:true; Item { Layout.fillWidth:true }; SecondaryButton { text:"Open Media"; onClicked:root.navigateRequested("media") }; SecondaryButton { text:"Open Transcription"; enabled:!!controller.project.sourceMediaId; onClicked:root.navigateRequested("transcription") } }
    }
}
