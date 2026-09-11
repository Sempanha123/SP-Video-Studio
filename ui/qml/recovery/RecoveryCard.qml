import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
Rectangle {
    id: root; property var snapshot: ({}); signal recoverRequested(string snapshotId); signal savedRequested(string snapshotId); signal reviewRequested(string snapshotId); signal discardRequested(string snapshotId)
    Layout.fillWidth: true; implicitHeight: content.implicitHeight + 28; radius: 12; color: Theme.colors.surface; border.color: Theme.colors.border
    ColumnLayout { id: content; anchors.fill: parent; anchors.margins: 14; spacing: 8
        Text { text: snapshot.projectTitle || snapshot.projectId || "Project"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold }
        Text { text: "Recovered " + (snapshot.createdAt || "") + "  ·  Revision " + (snapshot.projectRevision || 0); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: 11 }
        Text { visible: (snapshot.missingMedia || 0) > 0; text: "Recovered with Missing Media · use the existing relink workflow"; color: Theme.colors.warning; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        RowLayout { spacing: 8; Layout.fillWidth: true
            Button { text: "Recover"; onClicked: root.recoverRequested(String(snapshot.id || "")) }
            Button { text: "Open Saved Version"; onClicked: root.savedRequested(String(snapshot.id || "")) }
            Button { text: "Review"; onClicked: root.reviewRequested(String(snapshot.id || "")) }
            Item { Layout.fillWidth: true }
            Button { text: "Discard Recovery"; onClicked: root.discardRequested(String(snapshot.id || "")) }
        }
    }
}
