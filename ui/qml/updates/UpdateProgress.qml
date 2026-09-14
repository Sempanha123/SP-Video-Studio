import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Updates 1.0
import "../theme"
import "../components"

ColumnLayout {
    spacing: Theme.spacing.md
    ProgressBar { Layout.fillWidth: true; from: 0; to: 1; value: Updates.progress }
    RowLayout {
        Layout.fillWidth: true
        Text { text: Math.round(Updates.progress * 100) + "%"; color: Theme.colors.textSecondary; font.family: Theme.type.family }
        Item { Layout.fillWidth: true }
        SecondaryButton { text: "Cancel"; enabled: Updates.state === "downloading"; onClicked: Updates.cancelDownload() }
    }
}
