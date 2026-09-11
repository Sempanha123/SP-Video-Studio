import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
ColumnLayout {
    property var comparison: ({}); spacing: 6
    Repeater { model: ["Script", "Scenes", "Timeline", "Subtitles", "Translation", "Speakers", "News", "Story", "Shorts"]
        delegate: RowLayout { Layout.fillWidth: true; property var value: comparison[modelData] || ({})
            Text { text: modelData; color: Theme.colors.textSecondary; font.family: Theme.type.family; Layout.preferredWidth: 110 }
            Text { text: value.changed ? (modelData === "Scenes" ? String(value.delta || 0) + " changed" : "Changed") : "No newer changes"; color: value.changed ? Theme.colors.textPrimary : Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: 12 }
        }
    }
}
