import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    ScrollView { anchors.fill: parent; clip: true; contentWidth: availableWidth
        ColumnLayout { width: parent.width; spacing: Theme.spacing.xl
            ColumnLayout { Layout.fillWidth: true; spacing: 2
                Text { text: "Templates"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                Text { text: "A preview of reusable visual directions for future projects."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body }
            }
            GridLayout { Layout.fillWidth: true; columns: width < 800 ? 2 : 3; columnSpacing: Theme.spacing.lg; rowSpacing: Theme.spacing.lg
                TemplateCard { Layout.fillWidth: true; templateName: "Breaking News"; description: "Focused headline treatment"; iconName: "news" }
                TemplateCard { Layout.fillWidth: true; templateName: "Modern News"; description: "Clean editorial presentation"; iconName: "news" }
                TemplateCard { Layout.fillWidth: true; templateName: "Creator Shorts"; description: "Fast vertical creator layout"; iconName: "shorts" }
                TemplateCard { Layout.fillWidth: true; templateName: "Documentary"; description: "Measured cinematic storytelling"; iconName: "video" }
                TemplateCard { Layout.fillWidth: true; templateName: "Story"; description: "Warm narrative presentation"; iconName: "story" }
                TemplateCard { Layout.fillWidth: true; templateName: "Minimal"; description: "Quiet and flexible foundation"; iconName: "template" }
            }
        }
    }
}
